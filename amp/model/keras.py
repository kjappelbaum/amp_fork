#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'Kevin M. Jablonka'
__maintainer__ = 'Kevin M. Jablonka'
__email__ = 'kevin.jablonka@epfl.ch'
__date__ = '17.02.19'
__status__ = 'First Draft, Testing'

from keras.layers import Input, Dense, Dropout, GaussianDropout, Add


class KerasNN():
    """
    Using keras to create a atomistic NNP use GPU acceleration from either PyTorch or TF
    avoid a bit the api changes in TF and making it easier to maintain.

    In the end, I also want to play with convolutional and bayesian nets.
    """

    def elemental_net(self, hidden_layers=None, dropout=False, gaussian_dropout=0.4, activation='relu', fp_length=None, element=None):
        """
        Constructs a MLP network for one element type.

        Parameters
        ----------
        hidden_layers (list): List of integers specifying the number of neuros in each layer
        dropout (float): Float specifying the dropout rate
        gaussian_dropout (float): Float specifying the Gaussian dropout rate (default 0.4)
        activation (str): String specifying the activation function. Default: relu
        fp_length (int): Fingerprint length, used to specify the input shape
        element (str): Name of the element, used as input label, useful in the compilation of the model, can provide a
        dictionary with input where the elements are the keys.

        Returns
        -------

        """
        assert hidden_layers is not None; 'No hidden layer architecture provided to constructor'

        input = Input(shape=(fp_length,), dtype='float32', name=element)

        x = Dense(hidden_layer[0], activation=activation)(input)
        if dropout:
            x = Dropout(dropout)
        elif gaussian_dropout:
            x = GaussianDropout(gaussian_dropout)

        for hidden_layer in hidden_layers[1:]:
            x = Dense(hidden_layer, activation=activation)(x)
            if dropout:
                x = Dropout(dropout)
            elif gaussian_dropout:
                x = GaussianDropout(gaussian_dropout)

        x = Dense(1, activation='linear')(x)

        return x

    def add_elemental_net(self, elemental_net_list):
        merged_elemental_nets = Add()(elemental_net_list)

        return merged_elemental_nets

    def contruct_complete_ne(self):
        """
        Pseudocode:
        Get elements from fingerprint
        Get dictionary (different architecture for different elements) or list with architectures -> Create models
        Add them together.
        :return:
        """

        