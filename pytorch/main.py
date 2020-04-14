import os
import sys
import json
from itertools import product

import numpy as np
import torch

from torch import nn, optim

from utils.Worker import Worker
from utils.Data_Prepper import Data_Prepper
from utils.Federated_Learner import Federated_Learner
from utils.models import LogisticRegression, MLP_LogReg, MLP_Net, CNN_Net


use_cuda = False
args_space = {
	# system parameters
	'device': torch.device("cuda" if torch.cuda.is_available() and use_cuda else "cpu"),
	# setting parameters
	'dataset': 'adult',
	'sample_size_cap': [5000, 10000, 15000],
	'n_workers': [5, 10, 20],
	'split': 'powerlaw',
	'sharing_lambda': 0.1,  # privacy level -> at most (sharing_lambda * num_of_parameters) updates
	'batch_size' : 16,
	'train_val_split_ratio': 0.9,

	# model parameters
	'model_fn': LogisticRegression,
	'optimizer_fn': optim.SGD,
	'loss_fn': nn.CrossEntropyLoss(),
	'lr': 0.0001,

	# training parameters
	'pretrain_epochs': 5,
	'fl_epochs': [10, 20],
	'fl_individual_epochs': 5,
}


args = {
	# system parameters
	'device': torch.device("cuda" if torch.cuda.is_available() and use_cuda else "cpu"),
	# setting parameters
	'dataset': 'adult',
	'sample_size_cap': 15000,
	'n_workers': 5,
	'split': 'powerlaw',
	'sharing_lambda': 0.1,  # privacy level -> at most (sharing_lambda * num_of_parameters) updates
	'batch_size' : 16,
	'train_val_split_ratio': 0.9,

	# model parameters
	'model_fn': LogisticRegression,
	'optimizer_fn': optim.SGD,
	'loss_fn': nn.CrossEntropyLoss(),
	'lr': 0.0001,

	# training parameters
	'pretrain_epochs': 10,
	'fl_epochs': 20,
	'fl_individual_epochs': 5,
}


def run_experiments(args, repeat=5):
	# init steps
	logs_dir = 'logs'
	subdir = "{}_p{}_e{}-{}-{}_b{}_size{}_lr{}".format(args['split'],args['n_workers'], 
							args['pretrain_epochs'], args['fl_epochs'], args['fl_individual_epochs'],
							args['batch_size'], args['sample_size_cap'], args['lr'])
	logdir = os.path.join(logs_dir, subdir)
	try:
		os.mkdir(logdir)
	except:
		pass
	
	try:
		with open(os.path.join(logdir, 'complete.txt'), 'r') as file:
			if file.read() == 'complete':
				return
	except:
		pass

	log = open(os.path.join(logdir, 'log'), "w")
	sys.stdout = log
	print("Experimental settings are: ", args)
	
	performance_dicts = []
	for i in range(repeat):
		print("Experiment : No.{}/{}".format(str(i+1) ,str(repeat)))
		data_prep = Data_Prepper(args['dataset'], train_batch_size=args['batch_size'], sample_size_cap=args['sample_size_cap'], train_val_split_ratio=args['train_val_split_ratio'])
		federated_learner = Federated_Learner(args, data_prep)

		# train
		federated_learner.train()
		# analyze
		federated_learner.get_fairness_analysis()

		performance_dicts.append(federated_learner.performance_dict)
	
	keys = ['standalone_vs_final_corr', 'sharingcontribution_vs_final_corr', 'standalone_vs_federated_perturbed_corr',
			'federated_final_performance', 'CFFL_best_worker', 'standalone_best_worker' ]
	
	aggregate_dict = {}
	for key in keys:
		list_of_performance = [performance_dict[key] for performance_dict in performance_dicts]
		aggregate_dict[key] = np.array(list_of_performance).tolist()
		aggregate_dict[key +'_mean'] = np.mean(aggregate_dict[key], axis=0).tolist()
		aggregate_dict[key +'_std'] = np.std(aggregate_dict[key], axis=0).tolist()

		print(key, aggregate_dict[key])
		print(key +'_mean', aggregate_dict[key +'_mean'])
		print(key +'_std', aggregate_dict[key +'_std'])

	with open(os.path.join(logdir, 'aggregate_dict.txt'), 'w') as file:
		file.write(json.dumps(aggregate_dict))

	with open(os.path.join(logdir, 'complete.txt'), 'w') as file:
		file.write('complete')
	return


if __name__ == '__main__':
	# # init steps

	n_workers_space = [5, 10, 20]
	sample_size_cap_space = [5000, 10000, 15000]
	fl_epochs_space = [10, 20]

	[[5, 5000, 50],[10, 10000, 50],[20, 15000, 50]]

	# for n_workers, sample_size_cap, fl_epochs in product(n_workers_space, sample_size_cap_space, fl_epochs_space):
	for n_workers, sample_size_cap, fl_epochs in [[5, 5000, 50],[10, 10000, 50],[20, 15000, 50]]:
		args['n_workers'] = n_workers
		args['sample_size_cap'] = sample_size_cap
		args['fl_epochs'] = fl_epochs

		run_experiments(args)

