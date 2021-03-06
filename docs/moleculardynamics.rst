.. _moleculardynamics:

==================================
Using *Amp* Potentials for Molecular Dynamics
==================================

Currently there are two approaches available to take the machine-learning parameters trained in *Amp* and use it to perform fast molecular dynamics simulations.
The first approach uses the `Knowledge Base for Interatomic Models <https://openkim.org/>`_ (KIM).
`LAMMPS <http://www.afs.enea.it/software/lammps/doc17/html/Section_packages.html#kim>`_ recognizes `kim` as a pair style that interfaces with the KIM repository of interatomic potentials.

To build LAMMPS with the KIM package you must first install the KIM API (library) on your system.
Below are the minimal steps you need to install the KIM API.
After KIM API is installed, you will need to install a specific version of LAMMMPS from Ryan Elliott's `repository <https://github.com/ellio167/lammps/tree/kim-v2-update>`_.

Finally we will need to install the model driver that is provided in the *Amp* repository.
In the followings we discuss each step of installation.
In this installation instruction, we assume that the following requirements are installed on your system:

* git
* make
* cmake (If it is not installed on your system see `here <https://cmake.org/install/>`_.)

**Note that, as both the LAMMPS version and the KIM API version used in this tutorial are still under development, we can only guarantee specific commit ID's to work, future commits may break part of this installation instruction, until a stable version of KIM API v2 compatible with LAMMPS is released.**

----------------------------------
Installation of KIM API v2
----------------------------------

The model driver provided in this repository is in the format of KIM API version 2.
So you will need to install version 2 of the KIM API.
The *master-v2* branch of the OpenKIM `repository <https://github.com/openkim/kim-api/tree/master-v2>`_ works well with LAMMPS and should be downloaded::

   $ git clone -b master-v2 https://github.com/openkim/kim-api.git

You can make sure that you are on the correct branch of *origin/master-v2* by::

   $ cd kim-api/
   $ git status

Next you can install KIM API v2 by simply (note you should have gone to the *kim-api* directory in the last step)::

   $ ./configure
   $ make
   $ sudo make install

**Important step:** Add the following aliase to the bash script `.bashrc` (or `.bash_profile`) in your home directory::

   $ export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$"/usr/local/lib/"

Now you are ready to list model and model drivers available in KIM API v2 by::

   $ kim-api-v2-collections-management list

or install and remove models and model drivers, etc.
For a detailed explanation of possible options see `here <https://openkim.org/kim-api/>`_.


----------------------------------
Building LAMMPS
----------------------------------

Clone LAMMPS source files from the *kim-v2-update* branch of Ryan Elliott's `repository <https://github.com/ellio167/lammps/tree/kim-v2-update>`_::

   $ git clone -b kim-v2-update https://github.com/ellio167/lammps.git

To make sure that the HEAD is on the correct branch, you can do::

   $ cd lammps/
   $ git status

which should tell that your branch is on the branch *origin/kim-v2-update*.

**Important bug-fixing step:** There is a bug in this version of LAMMPS on *kim-v2-update* branch, which should be fixed before proceeding further by::

   $ sed -i "s/modelWillNotRequestNeighborsOfNoncontributingParticles)/modelWillNotRequestNeighborsOfNoncontributingParticles, 0)/g" ./src/KIM/pair_kim.cpp


Now that the bug is fixed, we follow the instructions given `here <https://github.com/ellio167/lammps/tree/kim-v2-update/cmake#other-packages>`_ to build LAMMPS using *cmake*.
Briefly we first make a *build* folder and then build LAMMPS inside the folder::

   $ mkdir build
   $ cd build
   $ cmake -D CMAKE_C_COMPILER=gcc -D CMAKE_CXX_COMPILER=g++ -D CMAKE_Fortran_COMPILER=gfortran -D PKG_KIM=on -D KIM_LIBRARY=$"/usr/local/lib//libkim-api-v2.so" -D KIM_INCLUDE_DIR=$"/usr/local/include/kim-api-v2" ../cmake
   $ make


----------------------------------
Installation of *amp_model_driver*
----------------------------------


Now you are ready to install the *amp_model_driver* provided on this repository.
To do that first move to *amp-kim* directory by::

   $ cd /amp_directory/tools/amp-kim/

where *amp_directory* is where your *Amp* source files are located.

Then make a copy of the fortran modules inside the *amp_model_driver* directory by::

   $ cp ../../amp/descriptor/gaussian.f90 amp_model_driver/gaussian.F90
   $ cp ../../amp/descriptor/cutoffs.f90 amp_model_driver/cutoffs.F90
   $ cp ../../amp/model/neuralnetwork.f90 amp_model_driver/neuralnetwork.F90

Finally you can install the *amp_model_driver* by::

   $ kim-api-v2-collections-management install user ./amp_model_driver

You can now remove the fortran modules that you copied earlier::

   $ rm amp_model_driver/gaussian.F90
   $ rm amp_model_driver/cutoffs.F90
   $ rm amp_model_driver/neuralnetwork.F90


----------------------------------
Installation of *amp_parametrized_model*
----------------------------------

Now that you have *amp_model_driver* installed, you need to install the parameters also as the final step.
**Note that this is the only step that you need to repeat when you change the parameters of the machine-learning model.**
You should first parse all of the parameters of your *Amp* calculator to a text file by


.. code-block:: python

 from amp import Amp
 from amp.convert import save_to_openkim
 
 calc = Amp(...)
 calc.train(...)
 save_to_openkim(calc)


where the last line parses the parameters of the calc object into a text file called `amp.params`.

You should then copy the generated text file into the *amp_parameterized_model* sub-directory of the *Amp* source directory::

   $ cp /working_directory/amp.params amp_directory/tools/amp-kim/amp_parameterized_model/.

where "working_directory" is where `amp.params` is located initially, and "amp_directory" is the directory of the *Amp* source files.
Finally you move back to the *amp-kim* directory by::

   $ cd /amp_directory/tools/amp-kim/

Note that installation of amp_parameterized_model will not work without amp.params being located in the /amp_directory/tools/amp-kim/ directory.
Next install your parameters by::

   $ kim-api-v2-collections-management install user ./amp_parameterized_model

Congrats!
Now you are ready to use the *Amp* calculator with `amp.params` in you molecular dynamics simulation by an input file like this


.. code-block:: bash

 variable	x index 1
 variable	y index 1
 variable	z index 1

 variable	xx equal 10*$x
 variable	yy equal 10*$y
 variable	zz equal 10*$z

 units		metal
 atom_style	atomic

 lattice        fcc 3.5
 region		box block 0 ${xx} 0 ${yy} 0 ${zz}
 create_box	1 box
 create_atoms	1 box
 mass		1 1.0

 velocity	all create 1.44 87287 loop geom

 pair_style      kim amp_parameterized_model
 pair_coeff	* * Pd

 neighbor	0.3 bin
 neigh_modify	delay 0 every 20 check no

 fix		1 all nve

 run		10


which, for example, is an input script for LAMMPS to do a molecular dynamics simulation of a Pd system for 10 units of time.

