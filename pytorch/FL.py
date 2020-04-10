# To mimic the running logic for federated learning


"""
1. get datasets and distribute them to workers
2. initialize the workers' models 
3. train their models locally for 10 epochs before 
4. average the locally trained models
5. start Federated Learning
6.
7.
8.

"""

import copy
import torch
import numpy as np
from torch import nn, optim
from torch.utils.data import DataLoader
from utils.Custom_Dataset import Custom_Dataset



# adult dataset
def prepare_dataset(name='adult', train_test=True, train=True, test=False):
    if name == 'adult':
        from utils.load_adult import get_train_test

        train_data, train_target, test_data, test_target = get_train_test()

        X_train = torch.tensor(train_data.values, requires_grad=False).float()
        y_train = torch.tensor(train_target.values, requires_grad=False).long()
        X_test = torch.tensor(test_data.values, requires_grad=False).float()
        y_test = torch.tensor(test_target.values, requires_grad=False).long()
        if train_test == True:
            return (X_train, y_train), (X_test, y_test)
        elif train == True:
            return X_train, y_train
        else:  # test==True:
            return X_test, y_test

train, test = prepare_dataset('adult', train_test=True)
X, y = train
X_test, y_test = test

train_val_split = 0.8
train_val_split_index = int(len(X) * 0.8)
X_train, y_train = X[:train_val_split_index], y[:train_val_split_index]
X_val, y_val = X[train_val_split_index:], y[train_val_split_index:]


from utils.utils import create_data_loader

val_loader = create_data_loader(X_val, y_val, batch_size=1000)
test_loader = create_data_loader(X_test, y_test, batch_size=1000)
print("datasets preparation successful")


from utils.models import LogisticRegression, MLP_LogReg

# User set argument
n_workers = 5
balanced_datasets=True

n_samples = 10000
use_cuda = True
device = torch.device("cuda" if torch.cuda.is_available() and use_cuda else "cpu" )
model_fn = LogisticRegression

np.random.seed(1111)

from utils.utils import random_split
indices_list = random_split(n_samples=n_samples, m_bins=n_workers, equal=balanced_datasets)


from utils.Worker import Worker
def init_workers(n_workers, X, y, indices_list, device):
    workers = []
    for i in range(n_workers):
        indices = indices_list[i]
        data = X[indices]
        target = y[indices]
        worker = Worker(data, target, indices, id=str(i), device=device)
        workers.append(worker)
    return workers

workers = init_workers(n_workers, X, y, indices_list, device)
print("Workers init successful")

input_dim, output_dim = X.shape[1], 2
for worker in workers:
    model = model_fn(input_dim, output_dim)
    optimizer = optim.SGD(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()

    worker.init_model_optimizer(model, optimizer, loss_fn)
    worker.init_train_loader(batch_size=16)
    worker.val_loader = val_loader
print("Workers' models and optimizer etc successful")



def distribute_points(points, marginal_contributions):
	# normalize so that the max is equal to n_workers - 1
	ratio = (len(points) - 1) / torch.max(marginal_contributions)
	marginal_contributions *= ratio
	print('resized contributions:', marginal_contributions)

	return points + marginal_contributions

def sort_grad_updates(grad_updates, marginal_contributions):
	# sort the grad_updates according to the marginal_contributions in a descending order
	return [(grad_update, worker_id) for grad_update, marg_contr, worker_id in sorted(zip(grad_updates, marginal_contributions, range(len(grad_updates ) )), key=lambda x:x[1], reverse=True)]

def acquire_update(point, worker, sorted_grad_updates):
	while point > 1:
		pass
	
	return grad_updates

from utils.utils import averge_models, average_gradient_updates, \
	add_update_to_model, compute_grad_update, compare_models,  \
	pretrain_locally, leave_one_out_evaluate, evaluate

# uncomment for local pretraining
pretrain_locally(workers, 2, test_loader)

models = [worker.model for worker in workers]
federated_model = averge_models(models, device=device)

points = torch.zeros((n_workers))

sharing_ledger = torch.zeros((n_workers)) 
print("\nStart federated learning ")
federated_epochs = 2
for epoch in range(federated_epochs):
	grad_updates = []
	for worker in workers:
		model_before = copy.deepcopy(worker.model)		
		worker.train_locally(2)
		model_after = copy.deepcopy(worker.model)
		grad_updates.append(compute_grad_update(model_before, model_after, device=device))

	# updates the federated model in function for efficiency
	marginal_contributions = leave_one_out_evaluate(federated_model, grad_updates, val_loader, device)
	print("Marginal contributions are: ", marginal_contributions)

	points = distribute_points(points, marginal_contributions)
	sorted_grad_updates = sort_grad_updates(grad_updates, marginal_contributions)

	for i, worker in enumerate(workers):
		acquired_updates = []
		
		for grad_update, worker_id in sorted_grad_updates:
			if worker_id != i and points[i] > 1: # not self and sufficient budget
				points[i] -= 1
				acquired_updates.append(grad_update)
				sharing_ledger[worker_id] += 1


		averaged_acquired_update = average_gradient_updates(acquired_updates)
		worker.model = add_update_to_model(worker.model, averaged_acquired_update, device=device)

	# averaged_update = average_gradient_updates(grad_updates, device=device)
	# federated_model = add_update_to_model(federated_model, averaged_update, device=device)
	evaluate(federated_model, test_loader, device)
	print("The number of gradient sharing by workers:", sharing_ledger)







 