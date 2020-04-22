import os
import shutil
import json
import pandas as pd
import ast
import numpy as np

from read_convergence import plot_convergence, parse, get_cffl_best

fairness_keys = [
		'standlone_vs_rrdssgd_mean',
		'standalone_vs_final_mean',
		'sharingcontribution_vs_final_mean', ]

performance_keys = [
		'dssgd',
		'standalone',
		'cffl',
		]

def collect_and_compile_performance(dirname, compiling_both=False):

	fairness_rows = []
	performance_rows = []
	for folder in os.listdir(dirname):
		if os.path.isfile(os.path.join(dirname, folder)) or not 'complete.txt' in os.listdir(os.path.join(dirname, folder)):
			continue

		setup = parse(folder)
		if compiling_both and setup['pretrain_epochs'] == 0: continue

		n_workers = int(folder.split('_')[1][1:])
		fl_epochs = int(folder.split('-')[1])
		theta = float(folder.split('_')[6].replace('theta', ''))
		try:
			with open(os.path.join(dirname, folder, 'aggregate_dict.txt')) as dict_log:
				aggregate_dict = json.loads(dict_log.read())
			f_data_row = ['P' + str(n_workers) + '_' + str(theta)] + [aggregate_dict[f_key][0] for f_key in fairness_keys]

			best_worker_accs = get_cffl_best(dirname, folder)
			p_data_row = ['P' + str(n_workers) + '_' + str(theta)] + best_worker_accs

			fairness_rows.append(f_data_row)
			performance_rows.append(p_data_row)
		except Exception as e:
			print(e)
			pass
			
	
	shorthand_f_keys = ['Distriubted', 'CFFL' ,'Contributions_V_final']
	fair_df = pd.DataFrame(fairness_rows, columns=[' '] + shorthand_f_keys).set_index(' ')
	fair_df = fair_df.sort_values(' ')
	print(fair_df.to_markdown())
	
	fair_df.to_csv( os.path.join(dirname, 'fairness.csv'))

	shorthand_p_keys = ['Distributed', 'Standalone', 'CFFL']
	pd.options.display.float_format = '{:,.2f}'.format
	perf_df = pd.DataFrame(performance_rows, columns=[' '] + shorthand_p_keys).set_index(' ').T
	perf_df = perf_df[sorted(perf_df.columns)]
	print(perf_df.to_markdown())
	perf_df.to_csv( os.path.join(dirname, 'performance.csv'))

	return fair_df, perf_df


def collate_pngs(dirname, compiling_both=False):
	try:
		os.mkdir(os.path.join(dirname, 'figures'))
	except:
		pass
	figures_dir = os.path.join(dirname, 'figures')
	
	for directory in os.listdir(dirname):
		if os.path.isfile(os.path.join(dirname, directory)) or not 'complete.txt' in os.listdir(os.path.join(dirname, directory)):
			continue

		setup = parse(directory)
		if compiling_both and setup['pretrain_epochs'] == 0: continue

		subdir = os.path.join(dirname, directory)

		# convert figure.png to
		# adult_LR_p5e100_cffl_localepoch5_localbatch16_lr0001_upload1
		figure_name = '{}_{}_p{}e{}_cffl_localepoch{}_localbatch{}_lr{}_upload{}.png'.format(
			setup['name'],  setup['model'],
			setup['P'], setup['Communication Rounds'],
			setup['E'], setup['B'],
			str(setup['lr']).replace('.', ''),
			str(setup['theta']).replace('.', '').rstrip('0'))
		shutil.copy(os.path.join(subdir,'figure.png'),  os.path.join(figures_dir, figure_name) )

		# convert standalone.png to
		# adult_LR_p5e100_standalone
		standalone_name = '{}_{}_p{}e{}_standalone.png'.format(
			setup['name'],  setup['model'],
			setup['P'], setup['Communication Rounds'])
		shutil.copy(os.path.join(subdir,'standlone.png'),   os.path.join(figures_dir, standalone_name) )

		# convert convergence_for_one.png to
		# adult_LR_p5e100_upload1_convergence
		convergence_name = '{}_{}_p{}e{}_upload{}_convergence.png'.format(
			setup['name'], setup['model'],
			setup['P'], setup['Communication Rounds'],
			str(setup['theta']).replace('.', '').rstrip('0'))
		shutil.copy(os.path.join(subdir,'convergence_for_one.png'),   os.path.join(figures_dir, convergence_name) )
	return



def run_all(dirname):
	print('Running performance scripts for {}'.format(dirname))
	experiment_results = plot_convergence(dirname)
	collate_pngs(dirname)
	fair_df, perf_df = collect_and_compile_performance(dirname)
	print()
	return

if __name__ == '__main__':

	'''
	1000perpartylr0001
	1000perparty
	500perparty
	'''

	COMPILING_BOTH = False
	TEST = True
	if TEST:
		dirname = 'logs/archive/latest_dropna_alpha3'
		# dirname = 'logs/adult/dropna_alpha3/credit_sum'
		# dirname = 'logs/adult/credit_sum'
		experiment_results = plot_convergence(dirname)
		collate_pngs(dirname, COMPILING_BOTH)
		fair_df, perf_df = collect_and_compile_performance(dirname, COMPILING_BOTH)
	else:
		dirname = 'logs/adult/na_a3_nopretrain/'
		for folder in ['credit_sum', 'sum']:
			run_all(os.path.join(dirname, folder))
