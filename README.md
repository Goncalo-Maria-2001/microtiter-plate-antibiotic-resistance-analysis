# Microtiter_plate_Antibiotic_Resistance_Analysis

Files used to obtain growth curve plots and growth parameter data in antibiotic resistance broth dilution assays done on 96-well plate, subjecting various strains to serial dillutions of various different antibiotics

## Overview 

The files take raw Tecan .csv output data and produce:

- A growth curve for each testing well containing essential model fit data,
- An average growth curve for each set of control wells for a given control,
- Estimated growth parameters for each testing well (Lag phase duration, Maximum growth rate, Maximum population size),
- Comparative growth parameter plots for each strain-antibiotic pair,
- Excel workbook containing the valuues of all parameters for each well.

## Getting started

Download plate_analysis.py (main file) and fill in your experiment data with the template provided in Example_plate_setup.txt (explained more carefully below), update the file paths and other parameters in the main file and run. The output will be a folder containing the growth curve plots for control and testing wells, growth parameter plots descriminated by strain and test and an excel workbook containing all the values obtained for the parameters.


## Functions

### plate_analysis.recursive_dict()

Defines a recursive default dict object for other functions to use.

### plate_analysis.get_plate_setup(path_to_plate_setup)

Input: path to a plate_setup.txt file with information detailing how the assay was done.

Output: generates a nested dictionary ("plate without data") which stores the information from the experiment in a structured way as displayed below:

<img width="1920" height="1080" alt="Dictionary (1)" src="https://github.com/user-attachments/assets/a796445f-c6eb-4c6d-8c1c-39cb791b7fa0" />

Where the tests, other controls, strains and replicates dictionaries can contain multiple dictionaries with the structure of test 1, control 1, strain 1 and replicate 1 respectively depending on the path_to_plate_setup provided.

### plate_analysis.add_plate_data(plate_setup,path)

Input: A "plate without data" dictionary and the path to the output of Tecan i-control plate reading converted to .csv

Output: A nested dictionary ("plate with data") with the following structure

<img width="1920" height="1080" alt="Dictionary" src="https://github.com/user-attachments/assets/0e15d5a7-5113-4f6e-b550-2ad0be9729a7" />

Where the tests, other controls, strains and replicates dictionaries can contain multiple dictionaries with the structure of test 1, control 1, strain 1 and replicate 1 respectively depending on the path_to_plate_setup provided.

### plate_analysis.create_save_dirs(plate,save_path):

Input: A "plate without data" or "plate with data" dictionary, path to place results folder

Output: nested dictionary of paths ("save directories") where the plots and excel workbooks will be saved with the structure presented below.

Creates the directories where the output plots and workbooks will be stored

<img width="1920" height="1080" alt="Dictionary" src="https://github.com/user-attachments/assets/4838b85d-87c4-4ca1-a158-8ab43cbaadd6" />



### plate_analysis.has_fittable_growth(df,min_OD_change):

Input: A pandas DataFrame with two columns: 'Time' and 'OD' representing the evolution of OD over time for a given well and a float corresponding to the minimun OD overall change in the well for which bacterial growth is considered to have occured

Output: True or False

Does a series of tests on the well data to determine if growth is considered to have occured

### plate_analysis.lag_phase_finder(df, slope_threshold):

Input: A pandas DataFrame with two columns: 'Time' and 'OD' representing the evolution of OD over time for a given well and
 a float represnting the population growth rate at which the log phase begins

Output: A float representing the cycle at which the lagphase ended

### plate_analysis.get_control_avg(plate, test, strain):

Input: A "plate with data" dictionary, a string corresponding to the name of a test, a string corresponding to the name of a strain

Output: A pandas dataframe with the columns: 'Time' with entries cycle numbers and 'OD' with entries the average OD of the control+ wells at the corresponding cycle

### plate_analysis.get_params_well(df, min_bic, min_OD_change, slope_threshold):

Input: A pandas DataFrame with two columns: 'Time' and 'OD' representing the evolution of OD over time for a given well, a float representing the maximum BIC for which a model is considered to have fit (min_bic), a float representing the minimum OD for which growth is considered to have occured (min_OD_change), a float representing the population growth rate at which the log phase begins

Output: A dictionary containing the values of each of the growth parameters studied (Lag phase duartion, maximum per capita growth rate, maximum OD) and the model name and BIC value

### plate_analysis.get_params_plate(plate, min_bic, min_OD_change, slope_threshold):

Input: A "plate with data" dictionary and min_bic, min_OD_change and slope-threshold as defined in plate_analysis.get_params_well

Output: A nested dictionary ("Params") containing the growth parameters for all testing wells organized as follows

<img width="1920" height="1080" alt="Strain 1" src="https://github.com/user-attachments/assets/47087084-ec24-480b-b98b-23ea1c79eb94" />


Where Parameters, strains, dilutions and replicates can have various, tests, strasins, dilutions and replicates nested dictionaries respectively.

### plate_analysis.plot_params(params, plate, save_paths, Max_OD_to_plot, Maxg_to_plot):

Input: A "Params" dictionary, a "plate with data" dictionary, a "save directories" dictionary, a float representing the maximum OD which is considered for plotting and a float representing the maximum growth rate considered for plotting

Output: Three plots per test per strain displaying information for each of the growth parameters studied

Each plot will be stored in its 'test/strain' directory

### plate_analysis.save_params(params, plate, save_paths):

Input: A "Params" dictionary, a "plate with data" dictionary, a "save directories" dictionary4

Output: For each test and strain pair an Excel workbook is generated containing information about each parameter's values

Each workbook will be stored in its 'test/strain' directory

### plate_analysis.save_growth_curves(plate, params, save_paths):

Input:  A "Params" dictionary, a "plate with data" dictionary, a "save directories" dictionary4

For each test strain and dilution combination, the data in the "plate with data" is plotted and saved as an imgae in each 'test/strain' directory, the plots also contain information on which model was used to obtain the parameters in the get_params functions.

## How to format plate_setup.txt files

The file must be divided into any number of test blocks followed by a negative controls block, separator lines were used in the examples in between tests and to set apart the control block, but this is not required. Only one antibiotic concentration may vary for each test.

Each test block is further divided into an intro section and the strain sections, there can be any number of strain sections.

The structure of the intro section should be as follows:

```
test_n: <name of test>
n_cycles: <number of cycles the tecan plate reader run for>
n_dilutions: <number of dilutions of the antibiotic tested in the plate>
n_strains: <number of strains in the test>
n_replicates: <number of replicates in the test>
antibiotic: <name of antibiotic in test>
concentrations: <concentrations in test separated by commas>
```

The structure of the strain blocks should be as follows:

```
strain: <name of strain>
color: <color map to use in plots>
replicate_n: <list of wells where replicate n is on the plate separated by commas>
.
. (there should be one line for each replicate)
.
control+: <list of wells where the positive control was performed separated by commas>
```

The structure of the negative control blocks should be as follows:

```
control-: <number of negative controls performed>
<name of negative control>: <wells in which the negative controls were performed>
. (there should be a line for each negative control performed in accordance with the number provided in the first line of the block)
.
```

## Example Output:

Growth curves plotted by plate_analysis.save_growth_curves:

<img width="640" height="480" alt="Strain_1 concentração 500 de Antibiotic_1" src="https://github.com/user-attachments/assets/0496e90c-9b8e-425a-806b-96cf899c7e0d" />

Comparative parameters plots generated by plate_analysis.plot_params:

<img width="1000" height="500" alt="Maximum OD as a function of Antibiotic_1 concentration for strain Strain_1" src="https://github.com/user-attachments/assets/25f353ec-9c83-44d7-9543-54dfbba5cbf6" />

Excel workbook sheet generated by plate_analysis.save_params:

<img width="997" height="194" alt="Screenshot From 2026-05-17 16-55-46" src="https://github.com/user-attachments/assets/78e2770f-3bf4-484e-af19-27083d250085" />

## Limitations 

The current files are not able to process a plate where mixtures of antibiotics where the concentrations of more then one of the antibiotics varies.
