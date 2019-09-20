from openchem.models.openchem_model import OpenChemModel

import torch


class Graph2Label(OpenChemModel):
    r"""
    Creates a model that predicts one or multiple labels given object of
    class graph as input. Consists of 'graph convolution neural network
    encoder'__, followed by 'graph max pooling layer'__ and
    multilayer perceptron.

    __https://arxiv.org/abs/1609.02907
    __https://pubs.acs.org/doi/full/10.1021/acscentsci.6b00367

    Args:
        params (dict): dictionary of parameters describing the model
            architecture.

    """
    def __init__(self, params):
        super(Graph2Label, self).__init__(params)
        self.encoder = self.params['encoder']
        self.encoder_params = self.params['encoder_params']
        self.Encoder = self.encoder(self.encoder_params, self.use_cuda)
        self.mlp = self.params['mlp']
        self.mlp_params = self.params['mlp_params']
        self.MLP = self.mlp(self.mlp_params)

    def forward(self, inp, eval=False):
        if eval:
            self.eval()
        else:
            self.train()
        output = self.Encoder(inp)
        output = self.MLP(output)
        return output

    def cast_inputs(self, sample):
        batch_adj = sample['adj_matrix'].to(torch.float)
        batch_x = sample['node_feature_matrix'].to(torch.float)
        batch_labels = sample['labels']
        if self.task == 'classification':
            batch_labels = batch_labels.to(torch.long)
        else:
            batch_labels = batch_labels.to(torch.float)
        if self.use_cuda:
            batch_x = batch_x.to(device='cuda')
            batch_adj = batch_adj.to(device='cuda')
            batch_labels = batch_labels.to(device='cuda')
        batch_inp = (batch_x, batch_adj)
        return batch_inp, batch_labels
