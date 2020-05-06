import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils import clip_grad_value_, clip_grad_norm_

import utils


class Custom_Dataset(Dataset):

	def __init__(self, X, y):
		self.X = X
		self.y = y
		self.count = len(X)

	def __len__(self):
		return self.count

	def __getitem__(self, idx):
		return self.X[idx], self.y[idx]


class Worker():

	def __init__(self, train_loader, model=None, optimizer=None,scheduler=None,
		model_pretrain=None, optimizer_pretrain=None, pretraining_lr=0.1, scheduler_pretrain=None,
		standalone_model=None, standalone_optimizer=None, standalone_scheduler=None,
		dssgd_model=None, dssgd_optimizer=None,dssgd_scheduler=None,
		loss_fn=None, theta=0.1, grad_clip=0.01, epoch_sample_size=-1,
		device=None,id=None,is_free_rider=False):

		self.train_loader = train_loader
		self.model = model
		self.optimizer = optimizer
		self.scheduler = scheduler
		self.model_pretrain = model_pretrain
		self.optimizer_pretrain = optimizer_pretrain
		self.pretraining_lr = pretraining_lr # specifically for the pretraining period
		self.scheduler_pretrain = scheduler_pretrain
		self.standalone_model = standalone_model
		self.standalone_optimizer = standalone_optimizer
		self.standalone_scheduler = standalone_scheduler
		self.dssgd_model = dssgd_model
		self.dssgd_optimizer = dssgd_optimizer
		self.dssgd_scheduler = dssgd_scheduler
		self.loss_fn = loss_fn
		self.theta = theta
		self.grad_clip = grad_clip		
		self.device = device
		self.id = id
		self.epoch_sample_size = epoch_sample_size
		self.param_count = sum([p.numel() for p in self.model.parameters()])
		self.is_free_rider = is_free_rider

	def train(self, epochs, is_pretrain=False):
		if self.is_free_rider:
			for model in [self.model, self.model_pretrain, self.dssgd_model, self.standalone_model]:
				model = model.to(self.device)
	
				for param in model.parameters():
					param.data += (torch.rand(param.data.shape) * 2 - 1).to(self.device) # * self.grad_clip
			return
		self.model_pretrain.train()
		self.model_pretrain = self.model_pretrain.to(self.device)

		self.model.train()
		self.model = self.model.to(self.device)

		self.standalone_model.train()
		self.standalone_model = self.standalone_model.to(self.device)

		self.dssgd_model.train()
		self.dssgd_model = self.dssgd_model.to(self.device)
		for epoch in range(int(epochs)):
			iter = 0
			for i, (batch_data, batch_target) in enumerate(self.train_loader):
				batch_data, batch_target = batch_data.to(
					self.device), batch_target.to(self.device)
				
				# pretrain model

				# introduce a slower pretraining process
				if is_pretrain:
					for g in self.optimizer_pretrain.param_groups:
					    g['lr'] = self.pretraining_lr

				self.optimizer_pretrain.zero_grad()
				outputs = self.model_pretrain(batch_data)
				loss = self.loss_fn(outputs, batch_target)
				loss.backward()
				self.optimizer_pretrain.step()
				iter += len(batch_data)

				# if pretrain, skip the rest
				if is_pretrain:
					continue

				# no pretrain model
				self.optimizer.zero_grad()
				outputs = self.model(batch_data)
				loss = self.loss_fn(outputs, batch_target)
				loss.backward()
				self.optimizer.step()

				# dssgd model
				self.dssgd_optimizer.zero_grad()
				outputs = self.dssgd_model(batch_data)
				loss = self.loss_fn(outputs, batch_target)
				loss.backward()
				self.dssgd_optimizer.step()

				# standalone model
				if not is_pretrain and epoch == 0:
					# standalone model does not include pre-train
					# standalone model only trains 1 epoch per communication round
					self.standalone_optimizer.zero_grad()
					outputs = self.standalone_model(batch_data)
					loss = self.loss_fn(outputs, batch_target)
					loss.backward()
					self.standalone_optimizer.step()

				if iter >= self.epoch_sample_size:
					# specifically for NLP task to terminate for training efficiency
					break

			if is_pretrain:
				# NO lr decay during pretraining
				continue
			self.scheduler_pretrain.step()
			self.scheduler.step()

			# using dssgd makes all local models converge to the same final model
			# self.dssgd_scheduler.step() 

			if not is_pretrain and epoch==0:
				self.standalone_scheduler.step()
