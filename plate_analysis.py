import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import json
import curveball.models as cb
import os
import argparse



def recursive_dict():
    return defaultdict(recursive_dict)

def get_plate_setup(path):
    plate = recursive_dict()
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('test_'):
                test_name = line.split(':')[1].strip()
                line = next(f).strip()
                n_cycles = int(line.split(':')[1].strip())
                plate[test_name]['n_cycles'] = n_cycles
                line = next(f).strip()
                n_dilutions = int(line.split(':')[1].strip())
                plate[test_name]['n_dilutions'] = n_dilutions
                line = next(f).strip()
                n_strains = int(line.split(':')[1].strip())
                plate[test_name]['n_strains'] = n_strains
                line = next(f).strip()
                n_replicates = int(line.split(':')[1].strip())
                plate[test_name]['n_replicates'] = n_replicates
                

            if line.startswith('antibiotic'):
                anti_name = line.split(':')[1].strip()
                line = next(f).strip()
                anti_concs = [value.strip() for value in line.split(':')[1].split(',')]
                plate[test_name]['antibiotic'] = anti_name
                plate[test_name]['antibiotic_concs'] = anti_concs
            
            if line.startswith('strain'):
                strain_name = line.split(':')[1].strip()
                line = next(f).strip()
                color = line.split(':')[1].strip()
                plate[test_name]['strains'][strain_name]['color'] = color
                n_replicates = plate[test_name]['n_replicates']
                for i in range(n_replicates):
                    line = next(f).strip()
                    replicate = i + 1
                    wells = [value.strip() for value in line.split(':')[1].split(',')]
                    plate[test_name]['strains'][strain_name]['replicates'][f'rep_{replicate}']['wells'] = wells
            
            if line.startswith('control+'):
                control_wells = [value.strip() for value in line.split(':')[1].split(',')]
                plate[test_name]['strains'][strain_name]['control+']['wells'] = control_wells

            if line.startswith('control-'):
                n_controls = int(line.split(':')[1])
                for i in range(n_controls):
                    line = next(f).strip()
                    control_name = line.split(':')[0].strip()
                    control_wells = [value.strip() for value in line.split(':')[1].split(',')]
                    plate['control-'][control_name]['wells'] = control_wells
        
        plate_setup = json.loads(json.dumps(plate))
    print(plate_setup)
    return plate_setup

def add_plate_data(plate_setup,path):
    
    df_raw = pd.read_csv(path, header=None, low_memory=False, encoding = 'latin1')
    header_rows = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains('Cycle Nr.', case=False).any(), axis=1)].index[0]
    df_data = pd.read_csv(path, skiprows=header_rows, encoding= 'latin1')
    
    plate_data = df_data.iloc[1::2].copy()
    plate_data = plate_data.dropna(axis=1, how='all')
    plate_data = plate_data.rename(columns={'Cycle Nr.': 'Well'}).set_index('Well')
    plate_data = plate_data.T

    for test in plate_setup:
        if test == 'control-':
            for control in plate_setup[test]:
                plate_setup[test][control]['data'] = []
                for well in plate_setup[test][control]['wells']:
                    plate_setup[test][control]['data'].append(pd.to_numeric(plate_data[well]).values)
        else:
            for strain in plate_setup[test]['strains']:
                plate_setup[test]['strains'][strain]['control+']['data'] = []
                for well in plate_setup[test]['strains'][strain]['control+']['wells']:
                    plate_setup[test]['strains'][strain]['control+']['data'].append(pd.to_numeric(plate_data[well]).values)
                for replicate in plate_setup[test]['strains'][strain]['replicates']:
                    plate_setup[test]['strains'][strain]['replicates'][replicate]['data'] = []
                    for well in plate_setup[test]['strains'][strain]['replicates'][replicate]['wells']:
                        plate_setup[test]['strains'][strain]['replicates'][replicate]['data'].append(pd.to_numeric(plate_data[well]).values)

    return plate_setup

def create_save_dirs(plate, save_path):
    save_paths_dict = dict()
    os.makedirs(os.path.join(save_path, 'results'), exist_ok=True)
    save_paths_dict['results'] = os.path.join(save_path, 'results')
    for test in plate:
        if test == 'control-':
            path = os.path.join(save_path, 'results', f'{test}')
            os.makedirs(path, exist_ok=True)
            save_paths_dict[test] = path
        else:
            save_paths_dict[test] = dict()
            for strain in plate[test]['strains']:
                path = os.path.join(save_path, 'results', f'{test}', 'curves', f'{strain}')
                os.makedirs(path, exist_ok=True)
                save_paths_dict[test][strain] = path
    return save_paths_dict

def has_fittable_growth(df, min_OD_change):
    if df['OD'].max() - df['OD'].min() < min_OD_change:
        return False
    else:
        try:
            models = cb.fit_model(df, PLOT=False, PRINT=False)
            return True
        except Exception as e:
            return False

def lag_phase_finder(df, slope_threshold):
    diffs = df['OD'].diff()
    mask = pd.Series(True, index=diffs.index)
    for i in range(5):
        mask = mask & (diffs.shift(-i) > slope_threshold)
    growth_start = df[mask]
    if not growth_start.empty:
        return growth_start.index[0]
    return np.nan

def get_control_avg(plate,test,strain):
    mega_list = []
    for i in range(len(plate[test]['strains'][strain]['control+']['data'])):
        mega_list.append(plate[test]['strains'][strain]['control+']['data'][i])
    return np.mean(mega_list, axis=0)

def save_growth_curves(params, plate, save_paths):
    for test in plate:
        if not test == 'control-':
            n_cycles = plate[test]['n_cycles']
            x = range(1, n_cycles + 1)
            n_dilutions = plate[test]['n_dilutions']
            n_replicates = plate[test]['n_replicates']
            for strain in plate[test]['strains']:
                color = plate[test]['strains'][strain]['color']
                cmap = plt.get_cmap(color)(np.linspace(0.4, 0.95, n_replicates))
                c_pos = get_control_avg(plate,test,strain)
                for i in range(n_dilutions):
                    plt.figure()
                    plt.title(f'{strain} subject to {plate[test]["antibiotic_concs"][i]} �g/mL of {plate[test]["antibiotic"]}')
                    plt.xlabel('Cycles')
                    plt.ylabel('OD')
                    plt.plot(x, c_pos, color='green', linestyle='--', label='controlo +')
                    j = 0
                    for replicate in plate[test]['strains'][strain]['replicates']:
                        model_name = params[test][strain]['dilutions'][plate[test]['antibiotic_concs'][i]]['replicates'][replicate]['Model']
                        bic = params[test][strain]['dilutions'][plate[test]['antibiotic_concs'][i]]['replicates'][replicate]['BIC']
                        plt.ylim(0.0, 2.0)
                        plt.plot(x, plate[test]['strains'][strain]['replicates'][replicate]['data'][i], color=cmap[j], label=f'strain - {strain}_{replicate}, model - {model_name}, BIC - {bic}')
                        j += 1
                    plt.legend(loc= 9, bbox_to_anchor=(0.5, -0.2))
                    plt.tight_layout()
                    plt.savefig(os.path.join(save_paths[test][strain], f'{strain} concentra��o {plate[test]["antibiotic_concs"][i]} de {plate[test]["antibiotic"]}.png'))
                    plt.close('all')
        else:
            for control in plate[test]:
                plt.figure(figsize=(10, 5))
                plt.title(f'{control}')
                plt.xlabel('Cycles')
                plt.ylabel('OD')
                plt.ylim(0.0, 2.0)
                y = np.mean(plate[test][control]['data'], axis = 0)
                plt.plot(x, y, color='green')
                plt.savefig(os.path.join(save_paths[test], f'{control}.png'))
                plt.close('all')
    print('growth curves saved')

def get_params_well(df, min_bic ,min_OD_change,slope_threshold):

    params_well = dict()
    if has_fittable_growth(df,min_OD_change):
        best_fit = cb.fit_model(df, PLOT=False, PRINT=False)[0]
        
        model_name = best_fit.model.__class__.__name__
        bic = best_fit.bic
        if bic < min_bic:
            maxg = cb.find_max_growth(best_fit, after_lag=True)[2]
            lag = cb.find_lag(best_fit)
            max_OD = best_fit.params.get('K').value

            params_well['Model'] = model_name
            params_well['BIC'] = bic
            params_well['Maximum Growth Rate'] = maxg
            params_well['Lag Phase'] = lag
            if max_OD < 5:
                params_well['Maximum OD'] = max_OD
            else:
                params_well['Maximum OD'] = None
        else:
            if df['OD'].max() - df['OD'].min() > min_OD_change:
                lag_alt = lag_phase_finder(df, slope_threshold)
                params_well['Lag Phase'] = lag_alt
            else:
                params_well['Lag Phase'] = None

            params_well['Model'] = 'No Growth fitted'
            params_well['BIC'] = '---'
            params_well['Maximum Growth Rate'] = None
            params_well['Maximum OD'] = None

    else:

        if df['OD'].max() - df['OD'].min() > min_OD_change:
            lag_alt = lag_phase_finder(df, slope_threshold)
            params_well['Lag Phase'] = lag_alt
        else:
            params_well['Lag Phase'] = None

        params_well['Model'] = 'No Growth fitted'
        params_well['BIC'] = '---'
        params_well['Maximum Growth Rate'] = None
        params_well['Maximum OD'] = None

    return params_well

def get_params_plate(plate, min_bic, min_OD_change, slope_threshold):

    dilutions_data = recursive_dict()

    for test in plate:
        if not test == 'control-':
            n_cycles = plate[test]['n_cycles']
            time = range(n_cycles)
            for strain in plate[test]['strains']:
                i = 0
                for dilution in plate[test]['antibiotic_concs']:
                    mega_list = []
                    for replicate in plate[test]['strains'][strain]['replicates']:
                        OD_data = plate[test]['strains'][strain]['replicates'][replicate]['data'][i]
                        dilutions_data[test][strain]['dilutions'][dilution]['replicates'][replicate] = pd.DataFrame({'Time': time, 'OD': OD_data})
                        mega_list.append(OD_data)
                    dilutions_data[test][strain]['dilutions'][dilution]['average'] = pd.DataFrame({'Time': time, 'OD': np.mean(mega_list, axis=0)})
                    i += 1
                control_data = get_control_avg(plate,test,strain)
                dilutions_data[test][strain]['control+'] = pd.DataFrame   ({'Time': time, 'OD': control_data})

    params = recursive_dict()

    for test in dilutions_data:
        for strain in dilutions_data[test]:
            for dilution in dilutions_data[test][strain]['dilutions']:
                for replicate in dilutions_data[test][strain]['dilutions'][dilution]['replicates']:
                    df = dilutions_data[test][strain]['dilutions'][dilution]['replicates'][replicate]
                    params_well = get_params_well(df, min_bic, min_OD_change,slope_threshold)
                    for param in params_well:
                        params[test][strain]['dilutions'][dilution]['replicates'][replicate][param] = params_well[param]

                df = dilutions_data[test][strain]['dilutions'][dilution]['average']
                params_well = get_params_well(df, min_bic, min_OD_change,slope_threshold)
                for param in params_well:
                    params[test][strain]['dilutions'][dilution]['average'][param] = params_well[param]
                print(f'dilution: {dilution} parameters handled')
            df = dilutions_data[test][strain]['control+']
            params_well = get_params_well(df, min_bic, min_OD_change,slope_threshold)
            for param in params_well:
                params[test][strain]['control+'][param] = params_well[param]



    return params

def plot_params(params, plate, save_paths, Max_OD_to_plot, Maxg_to_plot):
    params_list = ['Maximum Growth Rate', 'Lag Phase', 'Maximum OD']
    for test in params:
        x = plate[test]['antibiotic_concs']
        n_replicates = plate[test]['n_replicates']
        n_cycles = plate[test]['n_cycles']
        for param in params_list:
            for strain in params[test]:
                c_pos = params[test][strain]['control+'][param]
                color = plate[test]['strains'][strain]['color']
                cmap = plt.get_cmap(color)(np.linspace(0.4, 0.95, n_replicates))

                plt.figure(figsize=(10, 5))
                plt.title(f'{param} as a function of {plate[test]["antibiotic"]} concentration for strain {strain}')
                plt.xlabel('dilution')

                if param == 'Maximum Growth Rate':
                    plt.ylabel('1/Cycle')
                    plt.ylim(0, Maxg_to_plot)
                elif param == 'Lag Phase':
                    plt.ylabel('Number of Cycles')
                    plt.ylim(0, n_cycles)
                elif param == 'Maximum OD':
                    plt.ylim(0,Max_OD_to_plot)
                    plt.ylabel('OD')

                try:
                    plt.axhline(c_pos, color='green', linestyle='--', label='control +')
                except Exception as e:
                    print(f'Could not print positive control growth parameter {param} \n for strain {strain} because no growth was detected')

                y_avg = []
                for dilution in params[test][strain]['dilutions']:
                    i = 0

                    for replicate in params[test][strain]['dilutions'][dilution]['replicates']:
                        y = params[test][strain]['dilutions'][dilution]['replicates'][replicate][param]
                        if y == None:
                            y = -1
                        plt.plot(dilution, y, color=cmap[i], marker='o')
                        i += 1
                    y_avg.append(params[test][strain]['dilutions'][dilution]['average'][param])
                plt.scatter(x,y_avg, color=cmap[0], marker='*', label='parameter obtained from the average of replicates')
                plt.legend()
                plt.savefig(os.path.join(save_paths['results'],f'{test}', f'{param} as a function of {plate[test]["antibiotic"]} concentration for strain {strain}.png'))
                plt.close('all')

    print('params plotted')

def save_params(params, plate, save_paths):

    params_list = ['Maximum Growth Rate', 'Lag Phase', 'Maximum OD']
    test_dict = dict()
    for param in params_list:
        test_dict[param] = dict()
        test_dict[param]['control+'] = []
        test_dict[param]['Strain Replicate'] = []

    for test in params:

        for param in params_list:
            test_dict[param] = dict()
            test_dict[param]['Strain Replicate'] = []
            n_replicates = plate[test]['n_replicates']

        for param in params_list:
            for strain in params[test]:
                for k in range(1, n_replicates + 1):
                    test_dict[param]['Strain Replicate'].append(f'{strain}-rep_{k}')

        n_replicates = plate[test]['n_replicates']
        n_strains = plate[test]['n_strains']
        for strain in params[test]:
            for param in params_list:
                for k in range(1, n_replicates + 1):
                    for dilution in params[test][strain]['dilutions']:
                        test_dict[param][dilution] = []

        for param in params_list:
            test_dict[param]['control+'] = []
            for strain in params[test]:
                for dilution in params[test][strain]['dilutions']:
                    for replicate in params[test][strain]['dilutions'][dilution]['replicates']:
                        param_value = params[test][strain]['dilutions'][dilution]['replicates'][replicate][param]
                        test_dict[param][dilution].append(param_value)
                c_pos_val = params[test][strain]['control+'][param]
                padding_size = int(((n_strains * n_replicates)-n_strains)/n_strains)
                test_dict[param]['control+'].append(f'control + for strain {strain}: {c_pos_val:.2f}')
                for k in range(padding_size):
                    test_dict[param]['control+'].append(None)

        try:
            with pd.ExcelWriter(os.path.join(save_paths['results'],f'{test}', f'{test} parameter values.xlsx')) as writer:
                for param in test_dict:
                    df = pd.DataFrame(test_dict[param])
                    df.to_excel(writer, sheet_name= param, index = False, float_format = '%.2f')
        except Exception as e:
            print(r'Invalid Test Name, do not use characters like: . , \ / in test name')

    print('parameter values saved')
                
def main(args):
    plate_setup = get_plate_setup(args.setup)
    plate = add_plate_data(plate_setup, args.data)
    save_paths = create_save_dirs(plate, args.out)
    params = get_params_plate(plate, args.min_bic, args.min_od_change, args.slope_threshold)
    save_growth_curves(params, plate, save_paths)
    plot_params(params, plate, save_paths, args.max_od_to_plot, args.maxg_to_plot)
    save_params(params, plate, save_paths)
    print(f'Analysis complete, results saved to: {args.out}')

def parse_args():
    parser = argparse.ArgumentParser( description=('Generates growth curve plots and inferred growth parameters in broth microdilution assays done on a 96-well plate. '
                                                   'Produces growth parameter plots and records values in an excel workbook. '
                                                   'Input Tecan data converted to .csv format. '),  formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-s','--setup', required=True, help='Path to plate setup file')

    parser.add_argument('-d','--data', required=True, help='Path to plate data file')

    parser.add_argument('-o','--out', type= str, required=True, help='Output directory where results/ will be created')

    parser.add_argument('--min-od-change', default= 0.4, type=float, help='minimum OD net change for which bacterial growth is considered to have occured')

    parser.add_argument('--max-od-to-plot', type=float, default=2.5, help='Maximum \'reasonable\' OD to display in plot_params')

    parser.add_argument('--maxg-to-plot', type=float, default=0.5, help='Maximum \'reasonable\' Maximum Growth rate to display in plot_params')

    parser.add_argument('--slope-threshold', type=float, default=0.01, help='involved in lag_phase_finder function, a minimum slope of 0.01 must be detected for a series of consecutive cycles for the lag phase to be considered over')

    parser.add_argument('--min-bic', type=float, default=-350, help= 'Minimum BIC for which the model is considered to have fit well enough')

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
