import os
import sys
import json

import numpy as np
import torch

from torch import nn, optim

from utils.Worker import Worker
from utils.Data_Prepper import Data_Prepper
from utils.Federated_Learner import Federated_Learner


def run_experiments(args, repeat=5, logs_dir='logs'):
	update_gpu(args)

	# init steps
	print("Experimental settings are: ", args)
	
	performance_dicts = []
	performance_dicts_pretrain = []

	data_prep = Data_Prepper(args['dataset'], train_batch_size=args['batch_size'], n_workers=args['n_workers'], sample_size_cap=args['sample_size_cap'], train_val_split_ratio=args['train_val_split_ratio'], device=args['device'])
	for i in range(repeat):

		print("Experiment : No.{}/{}".format(str(i+1) ,str(repeat)))
		federated_learner = Federated_Learner(args, data_prep)

		# train
		federated_learner.train()

		# analyze
		federated_learner.get_fairness_analysis()

		performance_dicts.append(federated_learner.performance_dict)
		performance_dicts_pretrain.append(federated_learner.performance_dict_pretrain)

	
	keys = ['standalone_vs_final', 'standlone_vs_rrdssgd',
			'rr_dssgd_best', 'CFFL_best_worker', 'standalone_best_worker',
			# 'sharingcontribution_vs_improvements'
			# 'sharingcontribution_vs_final'
			 ]


	print("for all without pretraining:")
	aggregate_dict = {}
	for key in keys:
		list_of_performance = [performance_dict[key] for performance_dict in performance_dicts]
		aggregate_dict[key] = np.array(list_of_performance).tolist()
		aggregate_dict[key +'_mean'] = np.mean(aggregate_dict[key], axis=0).tolist()
		aggregate_dict[key +'_std'] = np.std(aggregate_dict[key], axis=0).tolist()

		# print(key, aggregate_dict[key])
		print(key +'_mean', aggregate_dict[key +'_mean'])
		# print(key +'_std', aggregate_dict[key +'_std'])
	
	print()
	print("for all the pretraining included:")
	aggregate_dict = {}
	for key in keys:
		list_of_performance = [performance_dict[key] for performance_dict in performance_dicts_pretrain]
		aggregate_dict[key] = np.array(list_of_performance).tolist()
		aggregate_dict[key +'_mean'] = np.mean(aggregate_dict[key], axis=0).tolist()
		aggregate_dict[key +'_std'] = np.std(aggregate_dict[key], axis=0).tolist()

		# print(key, aggregate_dict[key])
		print(key +'_mean', aggregate_dict[key +'_mean'])
		# print(key +'_std', aggregate_dict[key +'_std'])

	return


from arguments import adult_args, mnist_args, names_args, update_gpu, mr_args, sst_args, imdb_args

# from torch.multiprocessing import Pool, Process, set_start_method
# try:
# 	 set_start_method('spawn')
# except RuntimeError:
# 	pass


if __name__ == '__main__':
	# init steps
	# args = mnist_args
	args = mr_args
	args['n_workers'] = 5
	args['theta'] = 0.1 
	args['alpha'] = 1
	args['gamma'] = 0.977
	args['gpu'] = 0
	args['lr'] = 1e-6
	run_experiments(args, 1)
	
	exit()
	'''
	for n_workers, sample_size_cap,fl_epochs in[[5, 2000, 100]]: #, [10, 6000, 5]]:
		args['n_workers'] = n_workers
		args['sample_size_cap'] = sample_size_cap
		args['fl_epochs'] = fl_epochs
		# for lr in [0.1]:
		args['lr'] = 1e-5
		run_experiments(args, 2)
	'''