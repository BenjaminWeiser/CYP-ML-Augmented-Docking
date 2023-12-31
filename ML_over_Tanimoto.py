import gc
import os
import time
from collections import Counter

import numpy as np
import pandas as pd
import tensorflow as tf
from imblearn.over_sampling import SMOTE
from sklearn.metrics import roc_auc_score
from tensorflow import keras

import CYP_inhibition_functions
import Do_ML2

keras.backend.clear_session()

print(r"""
________________________________________________________________________________
 ______              _     _                                                        
|  ___ \            | |   (_)                                                       
| | _ | | ____  ____| | _  _ ____   ____                                            
| || || |/ _  |/ ___) || \| |  _ \ / _  )                                           
| || || ( ( | ( (___| | | | | | | ( (/ /                                            
|_||_||_|\_||_|\____)_| |_|_|_| |_|\____)                                                                            
 _                             _                                                    
| |                           (_)                                                   
| |      ____ ____  ____ ____  _ ____   ____                                        
| |     / _  ) _  |/ ___)  _ \| |  _ \ / _  |                                       
| |____( (/ ( ( | | |   | | | | | | | ( ( | |                                       
|_______)____)_||_|_|   |_| |_|_|_| |_|\_|| |                                       
                                      (_____|      _                                                     
   /\                                 _           | |                               
  /  \  _   _  ____ ____   ____ ____ | |_  ____ _ | |                               
 / /\ \| | | |/ _  |    \ / _  )  _ \|  _)/ _  ) || |                               
| |__| | |_| ( ( | | | | ( (/ /| | | | |_( (/ ( (_| |                               
|______|\____|\_|| |_|_|_|\____)_| |_|\___)____)____|                               
 _____       (_____|_     _                                                                                    
(____ \            | |   (_)                                                        
 _   \ \ ___   ____| |  _ _ ____   ____                                             
| |   | / _ \ / ___) | / ) |  _ \ / _  |                                            
| |__/ / |_| ( (___| |< (| | | | ( ( | |                                            
|_____/ \___/ \____)_| \_)_|_| |_|\_|| |                                            
                                 (_____|                                            



  __       ______ _     _ ______     _____       _     _ _     _      _             
 /  |     / _____) |   | (_____ \   (_____)     | |   (_) |   (_)_   (_)            
/_/ |    | /     | |___| |_____) )     _   ____ | | _  _| | _  _| |_  _  ___  ____  
  | |    | |      \_____/|  ____/     | | |  _ \| || \| | || \| |  _)| |/ _ \|  _ \ 
  | |_   | \_____   ___  | |         _| |_| | | | | | | | |_) ) | |__| | |_| | | | |
  |_(_)   \______) (___) |_|        (_____)_| |_|_| |_|_|____/|_|\___)_|\___/|_| |_|

____________________________________________________________________________________
____________________________________________________________________________________

                      Author: Benjamin Kachkowski Weiser
                        Date: September 6, 2023

This script embodies cutting-edge algorithms to augment traditional molecular docking, FITTED, processes
with machine learning for the prediction of Cytochrome P450 (CYP) enzyme inhibition.

Sections:

    1. Cleaned and combined test and train Pei sets with CYP_clean_files.ipnyb. Sets combined and then clustered to create new train and test sets
    2. Dock each ligand 5 times to its respective isoform using FITTED. Docked data can be found here: (to be inserted)
    3. Create analogue sets using FITTED. Create max train-test similarity using CYP_TC_DataSets.py
    4. Run RF with Feature Importances using max train-test similarity of 0.8 using ML_over_Tanimoto.py which calls CYP_inhibition_functions.py and Do_ML2.py
    5. Using these selected features run all ML models on all datasets using ML_over_Tanimoto.py which calls CYP_inhibition_functions.py and Do_ML2.py
    6. Use CYP_evaluate_and_ensemble.py which calls CYP_evaluate_and_ensemble_functions.py to make ensembles and evaluate and graph model performance

Please ensure you have all the required libraries installed.
For any issues or questions, please contact: benjamin.weiser@mail.mcgill.ca
Github: https://github.com/MoitessierLab/ML-augmented-docking-CYP-inhibition

____________________________________________________________________________________
____________________________________________________________________________________

""")

# Set seed
seed = 1
os.environ['PYTHONHASHEDSEED'] = str(seed)
np.random.seed(seed)
tf.random.set_seed(seed)

'''
Code Description:
1. Set Up: The script starts with a function load_parameters(), which contains the parameters for the entire machine 
    learning workflow. It then reads these parameters and sets up directories.
2. Data Preparation: It loads the active and inactive data for each Cytochrome P450 isoform in the loops for isoform in 
    pm['CYPs'], and for simu in pm['TCsimu']:. The active data contains known drugs or chemical compounds that the enzyme 
    acts on. The inactive data represents the compounds that the enzyme doesn't act on. The data is then cleaned.
3. Analog Clusters & Max Tanimoto Clusters: Depending on the parameters set in the load_parameters() function, it 
    loads either Analog Clustering or Max train-test Tanimoto Clustering to the data. 
4. Data Splitting: It splits the resultant data into training and test sets, based on the size defined in the 
    load_parameters() method.
5. Feature Selection: The script selects the appropriate features based on the parameters 
    set (if pm['select_feature_type'] == 1:). A feature in this context us ligand, docked, or all
6. Model Training: It trains several different machine learning models according to the set
     parameters (if pm['RF'] == 1:, if pm['KNN'] == 1:, if pm['LR'] == 1:, etc.). Models include 
     Random Forest (RF), K-nearest neighbors (KNN), Logistic Regression (LR), Gradient Boosting (GB), 
     a Deep Neural Network (DNN), and XGBoost (XGB). For each model, it uses the training data to learn patterns.
7. Model Evaluation: After each model is trained, it evaluates each model on the test data and 
    records performance metrics in a pandas DataFrame (results), which is eventually written to a CSV file.
8. Wrapping Up: After iterating over all the Cytochrome P450 isoforms and Tanimoto Similarities,
    the script closes by printing out the time of completion and the complete results.
'''

# Define Parameters
def load_parameters():
    # Parameters from params.json and exp.json loaded here to override parameters set below.
    pm = {'Project_name': 'Sep5_Allmodels',
          'dir': '/home/weiser/PYTHON/EnsembleLearning/CSVFiles/TanimotoCSV_Final',
          'data_dir': '/Results_CSV/',
          'fig_dir': 'Figures',
          'model_dir': 'Models',
          'CYPs': ['2C19', '3A4', '1A2', '2C9', '2D6'],  # defines isoforms to loop over
          'TCsimu': [30, 40, 50, 60, 70, 80],  # defines similarity [0.2, 0.3, 0.5, 0.8] to loop over
          'output_filename': '_Generated_EnsembleLearning_Models.txt',
          'evaluate_features': 0,  # if =1 than RF feature importances
          'perm_repeats': 7,  # for permutation test(suggest 15) for RF feature importances
          'PCA': 0,  # if =1 than principal component analysis PCA is on
          'RF': 1,  # if =1 than random forest is on
          'GB': 1,  # if =1 than gradient boosting is on
          'XGB_all': 0,  # if =1 than XGB is on with all, ligand, and docking features
          'XGB': 1,  # if =1 than XGB is on
          'KNN': 1,  # if =1 than KNN is on
          'LR': 1,  # if =1 than logistic regression is on
          'DNN': 1,  # if =1 than deep neural network is on
          'hyp_tune': 1,  # if =1 than hyp_tune is on for all model types
          'maxevals': 30,  # for hyp_tune number of evaluations
          'use_some_data': 0,  # if =1 than it is on and uses 'use_data_size'# for testing code!
          'use_data_size': 1000,  # size of data for testing code!
          'use_same_data_size': 1,  # if =1 than it is on and uses same data size as 0.3 max train-test tanimoto
          # similarity
          'test_size': 0.20,  # for train test split
          'calculate_Tanimoto': 0,  # if =1 than it is on and calculates tanimoto stats
          'analog_cluster': 0,  # if =1 than it is on and uses analog cluster
          'max_tan_cluster': 1,  # if =1 than it is on and uses max train-test tanimoto similarity cluster
          'select_feature_type': 0,  # if =1 than it is on and uses select_features_tanimoto to select feature type.
          # don't use for xgb_all
          # Chose Feature type
          # if features = 0 then rank/match score
          # if feature = 1 then use all ligand and docked feature
          # if feature = 2 then uses ligand features
          # if feature = 3 then uses docked features
          'save_model': 1  # if =1 than it is on and saves model
          }
    return pm


pm = load_parameters()
DATA_DIR = pm['data_dir']

# save the time we start
start_time = time.asctime(time.localtime(time.time()))

# Initial output
with open(pm['Project_name'] + pm['output_filename'], 'a') as fileOutput:
    fileOutput.write(
        '\n' + 'MACHINE LEARNING ACTIVATE' + '\n' + 'STARTING TRAINING' + '\n' + 'Made by Benjamin Kachkowski Weiser' + '\n' + 'Start Time:' + str(
            start_time) + '\n')
print("Start time: " + str(start_time))
print('MACHINE LEARNING ACTIVATE' + '\n' + 'STARTING TRAINING' + '\n' + 'Made by Benjamin Kachkowski Weiser')

# Set up folders
print(os.path.isdir(pm['dir'] + '/' + pm['Project_name'] + pm['model_dir']), '----',
      pm['dir'] + '/' + pm['Project_name'] + pm['model_dir'])
if os.path.isdir(pm['dir'] + '/' + pm['Project_name'] + pm['model_dir']) is False:
    os.mkdir(os.path.join(pm['dir'], pm['Project_name'] + pm['model_dir']))
    os.mkdir(os.path.join(pm['dir'], pm['Project_name'] + pm['fig_dir']))
# Set the directory where the data will be read


###########################################################################################
###########################################################################################
###########################################################################################
# Run ML Workflow
print('Initiating ML Workflow')
ii = 0  # indexer
results = [i for i in range(110)]
result_all = pd.DataFrame()

# For loop over all isoforms and then over all tanimoto similarities
for isoform in pm['CYPs']:  # for the isoforms
    for simu in pm['TCsimu']:  # defines similarity [0.2, 0.3, 0.5, 0.8]:
        print('   CYP ', isoform, ' ------ Cluster Tanimoto: ', simu)

        # Set up Data -- File format :  docked-actives-scored-20.csv
        activeData = pd.read_csv(pm['dir'] + DATA_DIR + isoform + '/' + isoform + '-docked-actives-scored' + '.csv')
        activeData['Activity'] = 1.0

        inactiveData = pd.read_csv(pm['dir'] + DATA_DIR + isoform + '/' + isoform + '-docked-inactives-scored' + '.csv')
        inactiveData['Activity'] = 0.0

        # Set up data set name
        data_set_name = str(isoform + '-' + str(simu))
        name = data_set_name.split('-')[0]
        print(data_set_name)
        # initiate result collection
        result = pd.DataFrame(columns=[data_set_name])

        # Use some data for testing purposes
        if pm['use_some_data'] == 1:
            inactiveData = inactiveData.head(pm['use_data_size'])
            activeData = activeData.head(pm['use_data_size'])

        # Find shapes of Data

        inactiveData = inactiveData.iloc[1:, :]  # delete first row
        num_of_actives_b = activeData.shape[0] - 1  # -1 for header
        num_of_inactives_b = inactiveData.shape[0]

        # To compare with original smiles list
        i_to_smiles = pd.read_csv(pm['dir'] + '/Smiles/' + isoform + '-inactive.smi', header=None, sep='\s+',
                                  names=['id', 'smiles'])
        i_to_smiles['Activity'] = 0.0
        a_to_smiles = pd.read_csv(pm['dir'] + '/Smiles/' + isoform + '-active.smi', header=None, sep='\s+',
                                  names=['id', 'smiles'])
        a_to_smiles['Activity'] = 1.0

        ###########################################################################
        # Clean Data - Make sure Active are actives and Inactives are inactives
        print('Cleaning Data')

        # make sure all activeData['id'] are in a_to_smiles using isin
        activeData['id'] = activeData['Molecule Name'].str.extract('(\d+)', expand=False).astype(int)
        inactiveData['id'] = inactiveData['Molecule Name'].str.extract('(\d+)', expand=False).astype(int)
        activeData = activeData[activeData['id'].isin(a_to_smiles['id'])]
        inactiveData = inactiveData[inactiveData['id'].isin(i_to_smiles['id'])]

        num_of_actives = activeData.shape[0] - 1
        num_of_inactives = inactiveData.shape[0]

        sizes = pd.DataFrame.from_dict(
            {'A shape': str(num_of_actives_b), 'I shape': str(num_of_inactives_b), 'A Final': str(num_of_actives),
             'I Final': str(num_of_inactives)}, orient='index', columns=[data_set_name])
        print(sizes)
        result_size = pd.concat({"Cleaning Sizes": sizes}, join='inner')
        result = pd.concat([result, result_size])

        ###########################################################################
        # Chose what Clusters to use and filter out from full data set
        data_activities = pd.concat([a_to_smiles, i_to_smiles], ignore_index=True)
        dataFrames = [activeData, inactiveData]
        data = pd.concat(dataFrames)


        #  For average Rankscore of inactive and actives
        print('Active Rank avg: ', activeData['RankScore'].mean())
        print('Inactive Rank avg: ', inactiveData['RankScore'].mean())
        dddd = activeData['RankScore'].mean() - inactiveData['RankScore'].mean()
        print('Difference: ', dddd)

        # make a new completely new dataframe with 'id', 'Activity' and FittedScore which is calculated using: data['RankScore'] - 0.16 * data['MatchScore']
        FittedData = pd.DataFrame({'id': data['id'], 'Activity': data['Activity'],
                                   'FittedScore': data['RankScore'] - 0.16 * data['MatchScore'],
                                   'RankScore': data['RankScore']})
        # Delete duplicate id's taking the one with the lowest FittedScore
        FittedData = FittedData.sort_values('FittedScore').drop_duplicates('id', keep='first')
        auc = roc_auc_score(-FittedData['Activity'], FittedData['FittedScore'])
        print(isoform, ' FITTED AUC: ', auc)

        print('Apply clusters')
        if pm['analog_cluster'] == 1:
            # read cluster_list_1a2-actives_10.txt from /home/benweiser/virtual/EnsembleLearning/CSVFiles/TanimotoCSV_Final/Analog_Clusters
            a_cluster_list = pd.read_csv(
                pm['dir'] + '/Analog_Clusters/cluster_list_' + isoform.lower() + '-actives_' + str(simu) + '.txt',
                header=None, names=['id'])
            i_cluster_list = pd.read_csv(
                pm['dir'] + '/Analog_Clusters/cluster_list_' + isoform.lower() + '-inactives_' + str(simu) + '.txt',
                header=None, names=['id'])
            # combine the two lists
            cluster_list = pd.concat([a_cluster_list, i_cluster_list])

            # filter data to only include the 'id' that are in clusters
            data = data[data['id'].isin(cluster_list['id'])]

            # Each id appears 5 times in data. Make it so that if the id only appears once in the cluster_list, take only the first row with that id from data and delete the rest of the rows with that id. If it appears three times in that cluster_list keep the first three row with that id and delete the rest. If cluster list is 858515858515 4239273 4240892 7976341, Then two row with 'id' 858515 are kept in data and one out of five rows of 4239273 are kept in data
            cluster_list_appearances = cluster_list['id'].value_counts()
            # if id has 1 appearance in cluster_list, keep the first row with that id in data and delete the rest
            # if id has 3 appearances in cluster_list, keep the first three rows with that id in data and delete the rest
            for id in cluster_list_appearances.index:
                n_appearances = cluster_list_appearances[id]
                if n_appearances < 5:
                    rows_to_delete = data[data['id'] == id].head(5 - n_appearances).index
                    data.drop(rows_to_delete, inplace=True)

            # get shape of data
            num_of_actives = data[data['Activity'] == 1.0].shape[0]
            num_of_inactives = data[data['Activity'] == 0.0].shape[0]

            print('Active size: ', num_of_actives, 'Inactive size: ', num_of_inactives)

        print('drop features')
        # Drop features
        data = data.dropna(axis=1)
        if 'name' in data.columns:
            data = data.drop(['name'], axis=1)
        if 'Molecule Name' in data.columns:
            # data = data.drop(['id'], axis=1)
            print('Selecting Features')
            data = CYP_inhibition_functions.drop_features(data, name)

        if pm['max_tan_cluster'] == 1:
            # read test_set_3A4.csv
            train_set_MT = pd.read_csv(
                pm['dir'] + '/Clusters_Max_TC/' + 'train_set_' + isoform + '_' + str(simu / 100) + '.csv')
            test_set_MT = pd.read_csv(pm['dir'] + '/Clusters_Max_TC/' + 'test_set_' + isoform + '.csv')
            # delete duplicate rows in trest_set_MT
            test_set_MT = test_set_MT.drop_duplicates(subset='id', keep='first')

            if pm['use_same_data_size'] == 1:
                # define same of train_set_MT
                # make dictionary if isoform and data size
                # size at tan = 30 since drop off of auc mostly stops here
                isoform_data_size = {'1A2': 2406, '2C9': 2622, '2C19': 2698, '2D6': 2789, '3A4': 2649}
                # randomly sample train_set_MT to be the size of the isoform_data_size
                print('All data of size : ', isoform_data_size[isoform])
                train_set_MT = train_set_MT.sample(n=isoform_data_size[isoform], random_state=1)

            # train_set is data that share id with train_set_MT
            train_set = data[data['id'].isin(train_set_MT['id'])]
            # test_set is data that share id with test_set_MT
            test_set = data[data['id'].isin(test_set_MT['id'])]
            # make X_train, y_train, X_test, y_test where y contains ['Activity']

            '''# For each 'id' take the two rows with the lowest value in column 'Energy'
            train_set = train_set.sort_values(by=['id', 'Energy'], ascending=[True, True])
            train_set = train_set.groupby('id').head(2)
            '''

            # write each test set to a csv file
            test_set.to_csv(pm['dir'] + '/Clusters_Max_TC/' + '80TC_complete_test_set_' + isoform + '.csv', index=False)

            # get stats on train_set
            num_of_actives = train_set[train_set['Activity'] == 1.0].shape[0]
            num_of_inactives = train_set[train_set['Activity'] == 0.0].shape[0]
            print('Train Max_tan_cluster Active size: ', num_of_actives, 'Inactive size: ', num_of_inactives)
            # get stats on test_set
            num_of_actives = test_set[test_set['Activity'] == 1.0].shape[0]
            num_of_inactives = test_set[test_set['Activity'] == 0.0].shape[0]
            print('Test Max_tan_cluster Active size: ', num_of_actives, 'Inactive size: ', num_of_inactives)

            y_train = train_set['Activity']
            X_train = train_set.drop(['Activity'], axis=1)

            y_test = test_set['Activity']
            X_test = test_set.drop(['Activity'], axis=1)
            del test_set_MT, train_set_MT

        ##############################################################################

        sizes = pd.DataFrame.from_dict({'auc': str(auc)}, orient='index', columns=[data_set_name])
        result_size = pd.concat({"auc": sizes}, join='inner')
        result = pd.concat([result, result_size])

        # make analog test set
        print('Make train and test sets')
        if pm['analog_cluster'] == 1:
            # Define test and train set for data names for tanimoto analysis
            train_size = 1 - pm['test_size']
            train_set = [data.iloc[0:int(num_of_actives * train_size)],
                         data.iloc[int(num_of_actives):int(num_of_actives + num_of_inactives * train_size)]]
            train_set = pd.concat(train_set)

            test_set = [data.iloc[int(num_of_actives * train_size):int(num_of_actives)], data.iloc[
                                                                                         int(num_of_actives + num_of_inactives * train_size):int(
                                                                                             num_of_inactives + num_of_actives)]]
            test_set = pd.concat(test_set)
            # save test set to csv
            test_set.to_csv(pm['dir'] + '/Analog_Clusters/' + isoform + str(simu) + '.csv', index=False)
            print('Analog test set saved to csv')

            # make X_train, y_train, X_test, y_test where y contains ['Activity']
            y_train = train_set['Activity']
            X_train = train_set.drop(['Activity'], axis=1)

            y_test = test_set['Activity']
            X_test = test_set.drop(['Activity'], axis=1)

        # finally drop id in X_train and X_test
        if 'id' in X_train.columns:
            X_train = X_train.drop(['id'], axis=1)
        if 'id' in X_test.columns:
            X_test = X_test.drop(['id'], axis=1)

        # get size of train and test sets
        train_size = X_train.shape[0]
        test_size = X_test.shape[0]

        sizes = pd.DataFrame.from_dict({'train size': str(train_size), 'test size': str(test_size)}, orient='index',
                                       columns=[data_set_name])
        print(sizes)
        result_size = pd.concat({"Data Sizes": sizes}, join='inner')
        result = pd.concat([result, result_size])

        if pm['calculate_Tanimoto'] == 1:
            # Get Tanimoto Stats
            # global id_in_test_train to say this are at intersection of train and test therfore delete in train
            id_to_smiles = pd.concat([a_to_smiles, i_to_smiles], ignore_index=True)
            id_to_smiles.columns = ['id', 'smiles', 'Activity']

            train_names = [x.split('_')[0] for x in data['Molecule Name']]
            test_names = [x.split('_')[0] for x in data['Molecule Name']]
            maxx, mean, std, max_avg = CYP_inhibition_functions.get_max_Tanimoto_from_smiles(train_names, test_names,
                                                                                             id_to_smiles)
            tan = pd.DataFrame.from_dict(
                {'max': str(maxx), 'mean': str(mean), 'std': str(std), 'max_avg': str(max_avg)}, orient='index',
                columns=[data_set_name])
            result_tan = pd.concat({"Tanimoto": tan}, join='inner')
            result = pd.concat([result, result_tan])

        counter = Counter(y_train)

        if counter[0] > counter[1]:
            ada = SMOTE(random_state=seed)
            X_train, y_train = ada.fit_resample(X_train, y_train)
        counter_aft = Counter(y_train)
        print('Before SMOTE', counter)
        print('After SMOTE', counter_aft)

        # Need to adjust PCA
        if pm['PCA'] == 1:
            print('Number of features before PCA ', X_train.shape[1])
            X_train, X_test = CYP_inhibition_functions.do_PCA(X_train, X_test)
            print('Number of feature after PCA', X_train.shape[1])

        X_train = X_train.convert_dtypes()
        X_test = X_test.convert_dtypes()

        if ii == 0:
            result_all = pd.DataFrame()

        # delete variable that are done being used to free up memory
        del data, FittedData, a_to_smiles, activeData, dataFrames, i_to_smiles, inactiveData,
        gc.collect()

        # Chose Feature type
        # if features = 0 then rank/match score
        # if feature = 1 then use all ligand and docked feature
        # if feature = 2 then uses ligand features
        # if feature = 3 then uses docked features
        if pm['select_feature_type'] == 1:
            feat_num = 1
            X_train, y_train = CYP_inhibition_functions.select_features_tanimoto(X_train, y_train, name,
                                                                                 features=feat_num)
            X_test, y_test = CYP_inhibition_functions.select_features_tanimoto(X_test, y_test, name, features=feat_num)
            print('Features used : ', X_train.columns.values.tolist())

        a = {}

        if pm['XGB_all'] == 1:
            # if features = 0 then rank/match score
            # if feature = 1 then use all ligand and docked feature
            # if feature = 2 then uses ligand features
            # if featuer = 3 then uses docked features
            print('All Features used : ', X_train.columns.values.tolist())
            score_gb = Do_ML2.Do_XGradientBoost(X_train, y_train, X_test, y_test, data_set_name + 'all', pm,
                                                a, seed)
            result_gb = pd.concat({"All_features": score_gb}, join='inner')
            result = pd.concat([result, result_gb])

            # Now with ligand features
            X_train_select, y_train2 = CYP_inhibition_functions.select_features_tanimoto(X_train, y_train, name,
                                                                                         features=2)
            X_test_select, y_test2 = CYP_inhibition_functions.select_features_tanimoto(X_test, y_test, name, features=2)
            print('Ligand Features used : ', X_train_select.columns.values.tolist())

            score_gb = Do_ML2.Do_XGradientBoost(X_train_select, y_train2, X_test_select, y_test2,
                                                data_set_name + 'ligand', pm, a, seed)
            result_gb = pd.concat({"Ligand_features": score_gb}, join='inner')
            result = pd.concat([result, result_gb])

            X_train_select, y_train3 = CYP_inhibition_functions.select_features_tanimoto(X_train, y_train, name,
                                                                                         features=3)
            X_test_select, y_test3 = CYP_inhibition_functions.select_features_tanimoto(X_test, y_test, name, features=3)

            print('Docking Features used : ', X_train_select.columns.values.tolist())
            score_gb = Do_ML2.Do_XGradientBoost(X_train_select, y_train3, X_test_select, y_test3,
                                                data_set_name + 'docked', pm, a, seed)
            result_gb = pd.concat({"Docked_features": score_gb}, join='inner')
            result = pd.concat([result, result_gb])

            result_fitted = pd.concat({"FITTED": pd.DataFrame({data_set_name: [auc]})}, join='inner')
            result = pd.concat([result, result_fitted])

        if pm['RF'] == 1:
            score_rf = Do_ML2.Do_RandomForest_FS(X_train, y_train, X_test, y_test, data_set_name, pm, a,
                                                 seed)  # X is trainvalidset, y is scores, name is name of isoform, pm is paramaters
            result_rf = pd.concat({"RF": score_rf}, join='inner')
            result = pd.concat([result, result_rf])

        if pm['KNN'] == 1:
            score_KNN = Do_ML2.Do_KNN(X_train, y_train, X_test, y_test, data_set_name, pm, a, seed)
            result_knn = pd.concat({"KNN": score_KNN}, join='inner')
            result = pd.concat([result, result_knn])

        if pm['LR'] == 1:
            score_LR = Do_ML2.Do_LR(X_train, y_train, X_test, y_test, data_set_name, pm, a, seed)
            result_lr = pd.concat({"LR": score_LR}, join='inner')
            result = pd.concat([result, result_lr])

        if pm['DNN'] == 1:
            score_DNN = Do_ML2.Do_DNN(X_train, y_train, X_test, y_test, data_set_name, pm, a, seed)
            result_dnn = pd.concat({"DNN": score_DNN}, join='inner')
            result = pd.concat([result, result_dnn])

        if pm['GB'] == 1:
            score_ggb = Do_ML2.Do_GradientBoost(X_train, y_train, X_test, y_test, data_set_name, pm, a, seed)
            result_ggb = pd.concat({"GB": score_ggb}, join='inner')
            result = pd.concat([result, result_ggb])

        if pm['XGB'] == 1:
            score_gb = Do_ML2.Do_XGradientBoost(X_train, y_train, X_test, y_test, data_set_name, pm, a, seed)
            result_gb = pd.concat({"XGB": score_gb}, join='inner')
            result = pd.concat([result, result_gb])

        results[ii] = result
        ii = ii + 1
        print(result)
        with open(pm['Project_name'] + pm['output_filename'], 'a') as fileOutput:
            fileOutput.write('File results: ' + str(result) + '\n')

    result_all = pd.concat(results[0:ii], axis=1)
    result_all.to_csv('result_all' + pm['Project_name'] + '.csv', index=False)

print('results : ', result_all)
end_time = time.asctime(time.localtime(time.time()))
with open(pm['Project_name'] + pm['output_filename'], 'a') as fileOutput:
    fileOutput.write('End time : ' + str(end_time) + '\n')
    fileOutput.write('Results : ' + str(result_all) + '\n')









# check auc of cyplebrity
'''cyplebrity = f"prediction_{isoform}.csv"
df_cyplebrity = pd.read_csv(pm['dir']+ '/' +cyplebrity)
dicttt = {'1A2': 1, '2C9': 2, '2C19': 3, '2D6': 4, '3A4': 5}

col_name = f'Prediction Model {dicttt[isoform]}'
# round each element in the column and store it back in the dataframe
df_cyplebrity[col_name] = df_cyplebrity[col_name].apply(lambda x: round(x))

# Merge data_activities and df_cyplebrity on the 'smiles' column
y_true = data_activities.rename(columns={'smiles': 'Input SMILES'}).merge(df_cyplebrity, on='Input SMILES',
                                                                          how='inner')

# Extract the y_pred_cyplebrity column after the merge
y_pred_cyplebrity = y_true[col_name]

# Now, y_true should only contain the 'Activity' column
y_true = y_true['Activity']

# Pass y_true and y_pred_cyplebrity to the testresults function
cyplebrity_results = CYP_inhibition_functions.testresults(y_true, y_pred_cyplebrity)
print('CYPlebrity: ', cyplebrity_results)'''