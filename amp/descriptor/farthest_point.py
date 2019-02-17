#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'Kevin M. Jablonka'
__maintainer__ = 'Kevin M. Jablonka'
__email__ = 'kevin.jablonka@epfl.ch'
__date__ = '17.02.19'
__status__ = 'First Draft, Testing'

import os
from ase.io import read, write
import pandas as pd
from tqdm import tqdm
from collections import Counter
from sklearn.cluster import KMeans
import numpy as np
from sklearn.metrics import pairwise_distances_argmin_min
from sklearn.decomposition import PCA


class FarthestPointSample():
    """
    Utility class that provides a training set that covers as much of the chemical space as possible
    to get the best generalization performance.
    
    First, we cluster in space for chemical composition, if this is not enough, we cluster in atomic 
    fingerprint space.

    In this way, we also avoid the problem of different chemical compositions when clustering fingerprints
    """

    def get_structures(self, directory, extension='.cif'):
        """Utillity function that provides a list with all structures in a directory"""
        return [
            os.abspath(os.path.join(directory, structure))
            for structure in os.listdir(directory)
            if structure.endswith(extension)
        ]

    def get_chemical_composition_space(self, structures):
        """
        ToDo:
            For less I/O combine this with the read stage for the fingerprint.

        Parameters
        ----------
        structures (list): list of paths to structures

        Returns
        -------
        pandas dataframe with element counts

        """
        composition_dict_list = []
        for structure in structures:
            atoms = read(structure)
            chemical_formula = Counter(atoms.get_chemical_formula(mode='all'))
            chemical_formula['path'] = structure
            composition_dict_list.append(chemical_formula)

        return pd.DataFrame(composition_dict_list).fillna(
            value=0, inplace=True)

    def cluster_composition_space(self, chemical_composition_df, n_clusters=3):
        kmeans = KMeans(n_clusters=n_clusters)
        X = chemical_composition_df.loc[:, chemical_composition_df.
                                        columns != 'path'].values()
        clusters = kmeans.fit_predict(X)

        # find now points closet to centroid
        closest, _ = pairwise_distances_argmin_min(clusters.cluster_centers_,
                                                   X)

        chemical_composition_df['cluster'] = clusters.labels_

        clustered_chemical_space = chemical_composition_df.groupby(
            'cluster')['path'].apply(lambda x: x.tolist()).to_dict()

        return closest, clustered_chemical_space

    def get_structural_pca(self, n_components=3):
        """
        Elementwise, we select tne n principal components of the structural fingerprint.

        Returns
        -------

        """

        reduced_fingerprints = []
        for structure in structures:
            reduced_fingerprint = []
            pca = PCA(n_components=n_components)
            for element, element_array in element_arrays.items():
                reduced_fingerprint.append(
                    pca.fit_transform(element_array).flatten())

            reduced_fingerprints.append({
                'structure':
                structure,
                'fingerprint':
                np.array(reduced_fingerprint).flatten()
            })

    def cluster_structural_space(self):
        ...

        kmeans = KMeans(n_clusters=n_clusters)
        X = chemical_composition_df.loc[:, chemical_composition_df.
                                        columns != 'path'].values()
        clusters = kmeans.fit_predict(X)

        # find now points closet to centroid
        closest, _ = pairwise_distances_argmin_min(clusters.cluster_centers_,
                                                   X)

        chemical_composition_df['cluster'] = clusters.labels_

        clustered_chemical_space = chemical_composition_df.groupby(
            'cluster')['path'].apply(lambda x: x.tolist()).to_dict()

        return closest, clustered_chemical_space
