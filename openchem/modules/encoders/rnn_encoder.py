import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from openchem.modules.encoders.openchem_encoder import OpenChemEncoder

from openchem.utils.utils import check_params

import numpy as np


class RNNEncoder(OpenChemEncoder):
    def __init__(self, params, use_cuda):
        super(RNNEncoder, self).__init__(params, use_cuda)
        check_params(params, self.get_required_params(),
                     self.get_optional_params())
        self.layer = self.params['layer']
        layers = ['LSTM', 'GRU', 'RNN']
        if self.layer not in ['LSTM', 'GRU', 'RNN']:
            raise ValueError(self.layer + ' is invalid value for argument'
                                          ' \'layer\'. Choose one from :'
                             + ', '.join(layers))

        self.input_size = self.params['input_size']
        self.encoder_dim = self.params['encoder_dim']
        self.n_layers = self.params['n_layers']
        if self.n_layers > 1:
            self.dropout = self.params['dropout']
        else:
            UserWarning('dropout can be non zero only when n_layers > 1. '
                        'Parameter dropout set to 0.')
            self.dropout = 0
        self.bidirectional = self.params['is_bidirectional']
        if self.bidirectional:
            self.n_directions = 2
        else:
            self.n_directions = 1
        if self.layer == 'LSTM':
            self.rnn = nn.LSTM(self.input_size, self.encoder_dim,
                               self.n_layers,
                               bidirectional=self.bidirectional,
                               dropout=self.dropout)
        elif self.layer == 'GRU':
            self.rnn = nn.GRU(self.input_size, self.encoder_dim,
                              self.n_layers,
                              bidirectional=self.bidirectional,
                              dropout=self.dropout)
        else:
            self.layer = nn.RNN(self.input_size, self.encoder_dim,
                                self.n_layers,
                                bidirectional=self.bidirectional,
                                dropout=self.dropout)

    @staticmethod
    def get_required_params():
        return {
            'input_size': int,
            'encoder_dim': int,
        }

    @staticmethod
    def get_optional_params():
        return{
            'layer': str,
            'n_layers': int,
            'dropout': float,
            'is_bidirectional': bool
        }

    def forward(self, inp, previous_hidden=None, pack=True):
        """
        inp: shape batch_size, seq_len, input_size
        previous_hidden: if given shape n_layers * num_directions,
        batch_size, embedding_dim.
               Initialized automatically if None
        return: embedded
        """
        input_tensor = inp[0]
        input_tensor = input_tensor.permute(1, 0, 2)
        input_length = inp[1]
        if pack:
            input_lengths_sorted, perm_idx = torch.sort(input_length, dim=0,
                                                        descending=True)
            input_lengths_sorted.cpu().numpy().tolist()
            input_tensor = torch.index_select(input_tensor, 1, perm_idx)
            rnn_input = pack_padded_sequence(input_tensor,
                                                input_lengths_sorted)
        else:
            rnn_input = input_tensor

        batch_size = input_tensor.size()[1]
        if previous_hidden is None:
            previous_hidden = self.init_hidden(batch_size)
            if self.layer == 'LSTM':
                cell = self.init_cell(batch_size)
                previous_hidden = (previous_hidden, cell)
        rnn_output, next_hidden = self.rnn(rnn_input, previous_hidden)

        if pack:
            rnn_output, _ = pad_packed_sequence(rnn_output)
            _, unperm_idx = perm_idx.sort(0)
            rnn_output = torch.index_select(rnn_output, 1, unperm_idx)

        index_tensor = input_length.cpu().numpy() - 1
        index_tensor = np.array([index_tensor]).astype('int')
        index_tensor = np.repeat(np.array([index_tensor]),
                                 repeats=rnn_output.size()[2],
                                 axis=0)
        index_tensor = index_tensor.swapaxes(0, 1)
        index_tensor = index_tensor.swapaxes(1, 2)
        index_tensor = torch.LongTensor(index_tensor).cuda()
        embedded = torch.gather(rnn_output, dim=0,
                                index=index_tensor).squeeze(0)

        return embedded, next_hidden

    def init_hidden(self, batch_size):
        if self.use_cuda:
            return torch.tensor(torch.zeros(self.n_layers * self.n_directions,
                                            batch_size,
                                            self.encoder_dim)).cuda()
        else:
            return torch.tensor(torch.zeros(self.n_layers * self.n_directions,
                                            batch_size,
                                            self.encoder_dim))

    def init_cell(self, batch_size):
        if self.use_cuda:
            return torch.tensor(torch.zeros(self.n_layers * self.n_directions,
                                            batch_size,
                                            self.encoder_dim)).cuda()
        else:
            return torch.tensor(torch.zeros(self.n_layers * self.n_directions,
                                            batch_size,
                                            self.encoder_dim))
