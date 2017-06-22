#!/usr/bin/env python

import numpy as np
import hashlib
import time
import os
import copy
import math
import random
import signal
import tarfile
import traceback
from datetime import datetime
from getpass import getuser
from ase import io as aseio
from ase.db import connect
try:
    import cPickle as pickle  # python2
except ImportError:
    import pickle  # python3


# Parallel processing ########################################################

def assign_cores(cores, log=None):
    """Tries to guess cores from environment.

    If fed a log object, will write its progress.
    """
    log = Logger(None) if log is None else log

    def fail(q, traceback_text=None):
        msg = ('Auto core detection is either not set up or not working for'
               ' your version of %s. You are invited to submit a patch to '
               'return a dictionary of the form {nodename: ncores} for this'
               ' batching system. The environment contents were dumped to '
               'the log file, as well as any traceback that caused the '
               'error.')
        log(msg % q)
        log('Environment dump:')
        for key, value in os.environ.iteritems():
            log('%s: %s' % (key, value))
        if traceback_text:
            log('\n' + '='*70 + '\nTraceback of last error encountered:')
            log(traceback_text)
        raise NotImplementedError(msg % q)

    def success(q, cores, log):
        log('Parallel configuration determined from environment for %s:' % q)
        for key, value in cores.iteritems():
            log('  %s: %i' % (key, value))

    if cores is not None:
        q = '<user-specified>'
        if cores == 1:
            log('Serial operation on one core specified.')
            return cores
        else:
            try:
                cores = int(cores)
            except TypeError:
                cores = cores
                success(q, cores, log)
                return cores
            else:
                cores = {'localhost': cores}
                success(q, cores, log)
                return cores

    if 'SLURM_NODELIST' in os.environ.keys():
        q = 'SLURM'
        try:
            nnodes = int(os.environ['SLURM_NNODES'])
            taskspernode = int(os.environ['SLURM_NTASKS_PER_NODE'])
            if nnodes == 1:
                cores = {'localhost': taskspernode}
            else:
                nodes = os.environ['SLURM_NODELIST']
                if '[' in nodes:
                    # Formatted funny like 'node[572,578]'.
                    prename, numbers = nodes.split('[')
                    numbers = numbers[:-1].split(',')
                    nodes = [prename + _ for _ in numbers]
                else:
                    nodes = nodes.split(',')
                cores = {node: taskspernode for node in nodes}
        except:
            # Get the traceback to log it.
            fail(q, traceback_text=traceback.format_exc())
    elif 'PBS_NODEFILE' in os.environ.keys():
        fail(q='PBS')
    elif 'LOADL_PROCESSOR_LIST' in os.environ.keys():
        fail(q='LOADL')
    elif 'PE_HOSTFILE' in os.environ.keys():
        q = 'SGE'
        try:
            hostfile = os.getenv('PE_HOSTFILE')
            cores = {}
            with open(hostfile) as f:
                for i, istr in enumerate(f):
                    hostname, nc = istr.split()[0:2]
                    nc = int(nc)
                    cores[hostname] = nc
        except:
            # Get the traceback to log it.
            fail(q, traceback_text=traceback.format_exc())
    else:
        import multiprocessing
        ncores = multiprocessing.cpu_count()
        cores = {'localhost': ncores}
        log('No queuing system detected; single machine assumed.')
        q = '<single machine>'
    success(q, cores, log)
    return cores


class MessageDictionary:
    """Standard container for all messages (typically requests, via
    zmq.context.socket.send_pyobj) sent from the workers to the master.

    This returns a simple dictionary. This is roughly email format.
    Initialize with process id (e.g., 'from'). Call with subject and data
    (body).
    """

    def __init__(self, process_id):
        self._process_id = process_id

    def __call__(self, subject, data=None):
        d = {'id': self._process_id,
             'subject': subject,
             'data': data}
        return d


def make_sublists(masterlist, n):
    """Randomly divides the masterlist into n sublists of roughly
    equal size.

    The intended use is to divide a keylist and assign
    keys to each task in parallel processing. This also destroys
    the masterlist (to save some memory).
    """
    np.random.shuffle(masterlist)
    N = len(masterlist)
    sublist_lengths = [
        N // n if _ >= (N % n) else N // n + 1 for _ in range(n)]
    sublists = []
    for sublist_length in sublist_lengths:
        sublists.append([masterlist.pop() for _ in xrange(sublist_length)])
    return sublists


def setup_parallel(parallel, workercommand, log):
    """Starts the worker processes and the master to control them.

    This makes an SSH connection to each node (including the one the master
    process runs on), then creates the specified number of processes on each
    node through its SSH connection. Then sets up ZMQ for efficienty
    communication between the worker processes and the master process.

    Uses the parallel dictionary as defined in amp.Amp. log is an Amp logger.
    module is the name of the module to be called, which is usually
    given by self.calc.__module, etc.
    workercommand is stub of the command used to start the servers,
    typically like "python -m amp.descriptor.gaussian". Appended to
    this will be " <pid> <serversocket> &" where <pid> is the unique ID
    assigned to each process and <serversocket> is the address of the
    server, like 'node321:34292'.

    Returns
    -------
    server : (a ZMQ socket)
        The ssh connections (pxssh instances; if these objects are destroyed
        pxssh will close the sessions)

        the pid_count, which is the total number of workers started. Each
        worker can be communicated directly through its PID, an integer
        between 0 and pid_count
    """
    import zmq
    from socket import gethostname

    log(' Parallel processing.')
    serverhostname = gethostname()

    # Establish server session.
    context = zmq.Context()
    server = context.socket(zmq.REP)
    port = server.bind_to_random_port('tcp://*')
    serversocket = '%s:%s' % (serverhostname, port)
    log(' Established server at %s.' % serversocket)

    workercommand += ' %s ' + serversocket

    log(' Establishing worker sessions.')
    connections = []
    pid_count = 0
    for workerhostname, nprocesses in parallel['cores'].iteritems():
        pids = range(pid_count, pid_count + nprocesses)
        pid_count += nprocesses
        connections.append(start_workers(pids,
                                         workerhostname,
                                         workercommand,
                                         log,
                                         parallel['envcommand']))

    return server, connections, pid_count


def start_workers(process_ids, workerhostname, workercommand, log,
                  envcommand):
    """A function to start a new SSH session and establish processes on
    that session.
    """
    if workerhostname != 'localhost':
        workercommand += ' &'
        log(' Starting non-local connections.')
        pxssh = importer('pxssh')
        ssh = pxssh.pxssh()
        ssh.login(workerhostname, getuser())
        if envcommand is not None:
            log('Environment command: %s' % envcommand)
            ssh.sendline(envcommand)
            ssh.readline()
        for process_id in process_ids:
            ssh.sendline(workercommand % process_id)
            ssh.expect('<amp-connect>')
            ssh.expect('<stderr>')
            log('  Session %i (%s): %s' %
                (process_id, workerhostname, ssh.before.strip()))
        return ssh
    import pexpect
    log(' Starting local connections.')
    children = []
    for process_id in process_ids:
        child = pexpect.spawn(workercommand % process_id)
        child.expect('<amp-connect>')
        child.expect('<stderr>')
        log('  Session %i (%s): %s' %
            (process_id, workerhostname, child.before.strip()))
        children.append(child)
    return children


# Data and logging ###########################################################


class FileDatabase:
    """Using a database file, such as shelve or sqlitedict, that can handle
    multiple processes writing to the file is hard.

    Therefore, we take the stupid approach of having each database entry be
    a separate file. This class behaves essentially like shelve, but saves each
    dictionary entry as a plain pickle file within the directory, with the
    filename corresponding to the dictionary key (which must be a string).

    Like shelve, this also keeps an internal (memory dictionary) representation
    of the variables that have been accessed.

    Also includes an archive feature, where files are instead added to a file
    called 'archive.tar.gz' to save disk space. If an entry exists in both the
    loose and archive formats, the loose is taken to be the new (correct)
    value.
    """

    def __init__(self, filename):
        """Open the filename at specified location. flag is ignored; this
        format is always capable of both reading and writing."""
        if not filename.endswith(os.extsep + 'ampdb'):
            filename += os.extsep + 'ampdb'
        self.path = filename
        self.loosepath = os.path.join(self.path, 'loose')
        self.tarpath = os.path.join(self.path, 'archive.tar.gz')
        if not os.path.exists(self.path):
            os.mkdir(self.path)
            os.mkdir(self.loosepath)
        self._memdict = {}  # Items already accessed; stored in memory.

    @classmethod
    def open(Cls, filename, flag=None):
        """Open present for compatibility with shelve. flag is ignored; this
        format is always capable of both reading and writing.
        """
        return Cls(filename=filename)

    def close(self):
        """Only present for compatibility with shelve.
        """
        return

    def keys(self):
        """Return list of keys, both of in-memory and out-of-memory
        items.
        """
        keys = os.listdir(self.loosepath)
        if os.path.exists(self.tarpath):
            with tarfile.open(self.tarpath) as tf:
                keys = list(set(keys + tf.getnames()))
        return keys

    def values(self):
        """Return list of values, both of in-memory and out-of-memory
        items. This moves all out-of-memory items into memory.
        """
        keys = self.keys()
        return [self[key] for key in keys]

    def __len__(self):
        return len(self.keys())

    def __setitem__(self, key, value):
        self._memdict[key] = value
        path = os.path.join(self.loosepath, str(key))
        if os.path.exists(path):
            with open(path, 'r') as f:
                if f.read() == pickle.dumps(value):
                    return  # Nothing to update.
        with open(path, 'w') as f:
            pickle.dump(value, f)

    def __getitem__(self, key):
        if key in self._memdict:
            return self._memdict[key]
        keypath = os.path.join(self.loosepath, key)
        if os.path.exists(keypath):
            with open(keypath, 'r') as f:
                return pickle.load(f)
        elif os.path.exists(self.tarpath):
            with tarfile.open(self.tarpath) as tf:
                return pickle.load(tf.extractfile(key))
        else:
            raise KeyError(str(key))

    def update(self, newitems):
        for key, value in newitems.iteritems():
            self.__setitem__(key, value)

    def archive(self):
        """Cleans up to save disk space and reduce huge number of files.

        That is, puts all files into an archive.  Compresses all files in
        <path>/loose and places them in <path>/archive.tar.gz.  If archive
        exists, appends/modifies.
        """
        loosefiles = os.listdir(self.loosepath)
        print('Contains %i loose entries.' % len(loosefiles))
        if len(loosefiles) == 0:
            print(' -> No action taken.')
            return
        if os.path.exists(self.tarpath):
            with tarfile.open(self.tarpath) as tf:
                names = [_ for _ in tf.getnames() if _ not in
                         os.listdir(self.loosepath)]
                for name in names:
                    tf.extract(member=name, path=self.loosepath)
        loosefiles = os.listdir(self.loosepath)
        print('Compressing %i entries.' % len(loosefiles))
        with tarfile.open(self.tarpath, 'w:gz') as tf:
            for file in loosefiles:
                tf.add(name=os.path.join(self.loosepath, file),
                       arcname=file)
        print('Cleaning up: removing %i files.' % len(loosefiles))
        for file in loosefiles:
            os.remove(os.path.join(self.loosepath, file))


class Data:
    """Serves as a container (dictionary-like) for (key, value) pairs that
    also serves to calculate them.

    Works by default with python's shelve module, but something that is built
    to share the same commands as shelve will work fine; just specify this in
    dbinstance.

    Designed to hold things like neighborlists, which have a hash, value
    format.

    This will work like a dictionary in that items can be accessed with
    data[key], but other advanced dictionary functions should be accessed with
    through the .d attribute:

    >>> data = Data(...)
    >>> data.open()
    >>> keys = data.d.keys()
    >>> values = data.d.values()
    """

    def __init__(self, filename, db=FileDatabase, calculator=None):
        self.calc = calculator
        self.db = db
        self.filename = filename
        self.d = None

    def calculate_items(self, images, parallel, log=None):
        """Calculates the data value with 'calculator' for the specified
        images.

        images is a dictionary, and the same keys will be used for the current
        database.
        """
        if log is None:
            log = Logger(None)
        if self.d is not None:
            self.d.close()
            self.d = None
        log(' Data stored in file %s.' % self.filename)
        d = self.db.open(self.filename, 'r')
        calcs_needed = list(set(images.keys()).difference(d.keys()))
        dblength = len(d)
        d.close()
        log(' File exists with %i total images, %i of which are needed.' %
            (dblength, len(images) - len(calcs_needed)))
        log(' %i new calculations needed.' % len(calcs_needed))
        if len(calcs_needed) == 0:
            return
        if parallel['cores'] == 1:
            d = self.db.open(self.filename, 'c')
            for key in calcs_needed:
                d[key] = self.calc.calculate(images[key], key)
            d.close()  # Necessary to get out of write mode and unlock?
            log(' Calculated %i new images.' % len(calcs_needed))
        else:
            workercommand = 'python -m %s' % self.calc.__module__
            server, connections, n_pids = setup_parallel(parallel,
                                                         workercommand, log)

            globals = self.calc.globals
            keyed = self.calc.keyed

            keys = make_sublists(calcs_needed, n_pids)
            results = {}

            # All incoming requests will be dictionaries with three keys.
            # d['id']: process id number, assigned when process created above.
            # d['subject']: what the message is asking for / telling you
            # d['data']: optional data passed from the worker.

            active = 0  # count of processes actively calculating
            log(' Parallel calculations starting...', tic='parallel')
            while True:
                message = server.recv_pyobj()
                if message['subject'] == '<purpose>':
                    server.send_pyobj(self.calc.parallel_command)
                    active += 1
                elif message['subject'] == '<request>':
                    request = message['data']  # Variable name.
                    if request == 'images':
                        server.send_pyobj({k: images[k] for k in
                                           keys[int(message['id'])]})
                    elif request in keyed:
                        server.send_pyobj({k: keyed[request][k] for k in
                                           keys[int(message['id'])]})
                    else:
                        server.send_pyobj(globals[request])
                elif message['subject'] == '<result>':
                    result = message['data']
                    server.send_string('meaningless reply')
                    active -= 1
                    log('  Process %s returned %i results.' %
                        (message['id'], len(result)))
                    results.update(result)
                elif message['subject'] == '<info>':
                    server.send_string('meaningless reply')
                if active == 0:
                    break
            log('  %i new results.' % len(results))
            log(' ...parallel calculations finished.', toc='parallel')
            log(' Adding new results to database.')
            d = self.db.open(self.filename, 'c')
            d.update(results)
            d.close()  # Necessary to get out of write mode and unlock?

        self.d = None

    def __getitem__(self, key):
        self.open()
        return self.d[key]

    def close(self):
        """Safely close the database.
        """
        if self.d:
            self.d.close()
        self.d = None

    def open(self, mode='r'):
        """Open the database connection with mode specified.
        """
        if self.d is None:
            self.d = self.db.open(self.filename, mode)

    def __del__(self):
        self.close()


class Logger:

    """Logger that can also deliver timing information.

    Parameters
    ----------
    file : str
        File object or path to the file to write to.  Or set to None for
        a logger that does nothing.
    """

    def __init__(self, file):
        if file is None:
            self.file = None
            return
        if isinstance(file, str):
            self.filename = file
            file = open(file, 'a')
        self.file = file
        self.tics = {}

    def tic(self, label=None):
        """Start a timer.

        Parameters
        ----------
        label : str
            Label for managing multiple timers.
        """
        if self.file is None:
            return
        if label:
            self.tics[label] = time.time()
        else:
            self._tic = time.time()

    def __call__(self, message, toc=None, tic=False):
        """Writes message to the log file.

        Parameters
        ---------
        message : str
            Message to be written.
        toc : bool or str
            If toc=True or toc=label, it will append timing information in
            minutes to the timer.
        tic : bool or str
            If tic=True or tic=label, will start the generic timer or a timer
            associated with label. Equivalent to self.tic(label).
        """
        if self.file is None:
            return
        dt = ''
        if toc:
            if toc is True:
                tic = self._tic
            else:
                tic = self.tics[toc]
            dt = (time.time() - tic) / 60.
            dt = ' %.1f min.' % dt
        if self.file.closed:
            self.file = open(self.filename, 'a')
        self.file.write(message + dt + '\n')
        self.file.flush()
        if tic:
            if tic is True:
                self.tic()
            else:
                self.tic(label=tic)


def make_filename(label, base_filename):
    """Creates a filename from the label and the base_filename which should be
    a string.

    Returns None if label is None; that is, it only saves output if a label is
    specified.

    Parameters
    ----------
    label : str
        Prefix.
    base_filename : str
        Basic name of the file.
    """

    if label is None:
        return None
    if not label:
        filename = base_filename
    else:
        filename = os.path.join(label + base_filename)

    return filename


# Images and hasing ##########################################################

def get_hash(atoms):
    """Creates a unique signature for a particular ASE atoms object.

    This is used to check whether an image has been seen before. This is just
    an md5 hash of a string representation of the atoms object.

    Parameters
    ----------
    atoms : ASE dict
        ASE atoms object.

    Returns
    -------
        Hash string key of 'atoms'.
    """
    string = str(atoms.pbc)
    for number in atoms.cell.flatten():
        string += '%.15f' % number
    string += str(atoms.get_atomic_numbers())
    for number in atoms.get_positions().flatten():
        string += '%.15f' % number

    md5 = hashlib.md5(string)
    hash = md5.hexdigest()
    return hash


def hash_images(images, log=None, ordered=False):
    """ Converts input images -- which may be a list, a trajectory file, or
    a database -- into a dictionary indexed by their hashes.

    Returns this dictionary. If ordered is True, returns an OrderedDict. When
    duplicate images are encountered (based on encountering an identical hash),
    a warning is written to the logfile. The number of duplicates of each image
    can be accessed by examinging dict_images.metadata['duplicates'], where
    dict_images is the returned dictionary.
    """
    if log is None:
        log = Logger(None)
    if images is None:
        return
    elif hasattr(images, 'keys'):
        log(' %i unique images after hashing.' % len(images))
        return images  # Apparently already hashed.
    else:
        # Need to be hashed, and possibly read from file.
        if isinstance(images, str):
            log('Attempting to read images from file %s.' %
                images)
            extension = os.path.splitext(images)[1]
            from ase import io
            if extension == '.traj':
                images = io.Trajectory(images, 'r')
            elif extension == '.db':
                images = [row.toatoms() for row in
                          connect(images, 'db').select(None)]

        # images converted to dictionary form; key is hash of image.
        log('Hashing images...', tic='hash')
        dict_images = MetaDict()
        dict_images.metadata['duplicates'] = {}
        dup = dict_images.metadata['duplicates']
        if ordered is True:
            from collections import OrderedDict
            dict_images = OrderedDict()
        for image in images:
            hash = get_hash(image)
            if hash in dict_images.keys():
                log('Warning: Duplicate image (based on identical hash).'
                    ' Was this expected? Hash: %s' % hash)
                if hash in dup.keys():
                    dup[hash] += 1
                else:
                    dup[hash] = 2
            dict_images[hash] = image
        log(' %i unique images after hashing.' % len(dict_images))
        log('...hashing completed.', toc='hash')
        return dict_images


def randomize_images(images, fraction=0.8):
    """Randomly assigns 'fraction' of the images to a training set and (1
    - 'fraction') to a test set. Returns two lists of ASE images.

    Parameters
    ----------
    images : list or str
        List of ASE atoms objects in ASE format. This can also be the path to
        an ASE trajectory (.traj) or database (.db) file.
    fraction : float
        Portion of train_images to all images.

    Returns
    -------
    train_images, test_images : list
        Lists of train and test images.
    """
    file_opened = False
    if type(images) == str:
        extension = os.path.splitext(images)[1]
        if extension == '.traj':
            images = aseio.Trajectory(images, 'r')
        elif extension == '.db':
            images = aseio.read(images)
        file_opened = True

    trainingsize = int(fraction * len(images))
    testsize = len(images) - trainingsize
    testindices = []
    while len(testindices) < testsize:
        next = np.random.randint(len(images))
        if next not in testindices:
            testindices.append(next)
    testindices.sort()
    trainindices = [index for index in range(len(images)) if index not in
                    testindices]
    train_images = [images[index] for index in trainindices]
    test_images = [images[index] for index in testindices]
    if file_opened:
        images.close()
    return train_images, test_images

# Custom exceptions ##########################################################


class ConvergenceOccurred(Exception):
    """ Kludge to decide when scipy's optimizers are complete.
    """
    pass


class TrainingConvergenceError(Exception):
    """Error to be raised if training does not converge.
    """
    pass


# Miscellaneous ##############################################################

def string2dict(text):
    """Converts a string into a dictionary.

    Basically just calls `eval` on it, but supplies words like OrderedDict and
    matrix.
    """
    try:
        dictionary = eval(text)
    except NameError:
        from collections import OrderedDict
        from numpy import array, matrix
        dictionary = eval(text)
    return dictionary


def now(with_utc=False):
    """
    Returns
    -------
        String of current time.
    """
    local = datetime.now().isoformat().split('.')[0]
    utc = datetime.utcnow().isoformat().split('.')[0]
    if with_utc:
        return '%s (%s UTC)' % (local, utc)
    else:
        return local


logo = """
   oo      o       o   oooooo
  o  o     oo     oo   o     o
 o    o    o o   o o   o     o
o      o   o  o o  o   o     o
oooooooo   o   o   o   oooooo
o      o   o       o   o
o      o   o       o   o
o      o   o       o   o
"""


def importer(name):
    """Handles strange import cases, like pxssh which might show
    up in eithr the package pexpect or pxssh.
    """

    if name == 'pxssh':
        try:
            import pxssh
        except ImportError:
            try:
                from pexpect import pxssh
            except ImportError:
                raise ImportError('pxssh not found!')
        return pxssh
    elif name == 'NeighborList':
        try:
            from ase.neighborlist import NeighborList
        except ImportError:
            # We're on ASE 3.10 or older
            from ase.calculators.neighborlist import NeighborList
        return NeighborList


# Amp Simulated Annealer ######################################################


class Annealer(object):

    """
    Inspired by the simulated annealing implementation of
    Richard J. Wagner <wagnerr@umich.edu> and
    Matthew T. Perry <perrygeo@gmail.com> at
    https://github.com/perrygeo/simanneal.

    Performs simulated annealing by calling functions to calculate loss and
    make moves on a state.  The temperature schedule for annealing may be
    provided manually or estimated automatically.

    Can be used by something like:

    >>> from amp import Amp
    >>> from amp.descriptor.gaussian import Gaussian
    >>> from amp.model.neuralnetwork import NeuralNetwork
    >>> calc = Amp(descriptor=Gaussian(), model=NeuralNetwork())

    which will initialize tha calc object as usual, and then

    >>> from amp.utilities import Annealer
    >>> Annealer(calc=calc, images=images)

    which will perform simulated annealing global search in parameters space,
    and finally

    >>> calc.train(images=images)

    for gradient descent optimization.
    """

    Tmax = 20.0             # Max (starting) temperature
    Tmin = 2.5              # Min (ending) temperature
    steps = 10000           # Number of iterations
    updates = steps / 200   # Number of updates (an update prints to log)
    copy_strategy = 'copy'
    user_exit = False
    save_state_on_exit = False

    def __init__(self, calc, images,
                 Tmax=None, Tmin=None, steps=None, updates=None):
        if Tmax is not None:
            self.Tmax = Tmax
        if Tmin is not None:
            self.Tmin = Tmin
        if steps is not None:
            self.steps = steps
        if updates is not None:
            self.updates = updates
        self.calc = calc

        self.calc._log('\nAmp simulated annealer started. ' + now() + '\n')
        self.calc._log('Descriptor: %s' %
                       self.calc.descriptor.__class__.__name__)
        self.calc._log('Model: %s' % self.calc.model.__class__.__name__)

        images = hash_images(images, log=self.calc._log)

        self.calc._log('\nDescriptor\n==========')
        # Derivatives of fingerprints need to be calculated if train_forces is
        # True.
        calculate_derivatives = True
        self.calc.descriptor.calculate_fingerprints(
            images=images,
            parallel=self.calc._parallel,
            log=self.calc._log,
            calculate_derivatives=calculate_derivatives)
        # Setting up calc.model.vector()
        self.calc.model.fit(trainingimages=images,
                            descriptor=self.calc.descriptor,
                            log=self.calc._log,
                            parallel=self.calc._parallel,
                            only_setup=True,)
        # Truning off ConvergenceOccured exception and log_losses
        initial_raise_ConvergenceOccurred = \
            self.calc.model.lossfunction.raise_ConvergenceOccurred
        initial_log_losses = self.calc.model.lossfunction.log_losses
        self.calc.model.lossfunction.log_losses = False
        self.calc.model.lossfunction.raise_ConvergenceOccurred = False
        initial_state = self.calc.model.vector.copy()
        self.state = self.copy_state(initial_state)

        signal.signal(signal.SIGINT, self.set_user_exit)
        self.calc._log('\nAnnealing\n=========\n')
        bestState, bestLoss = self.anneal()
        # Taking the best state
        self.calc.model.vector = np.array(bestState)
        # Returning back the changed arguments
        self.calc.model.lossfunction.log_losses = initial_log_losses
        self.calc.model.lossfunction.raise_ConvergenceOccurred = \
            initial_raise_ConvergenceOccurred
        # cleaning up sessions
        self.calc.model.lossfunction._step = 0
        self.calc.model.lossfunction._cleanup()
        calc = self.calc

    @staticmethod
    def round_figures(x, n):
        """Returns x rounded to n significant figures."""
        return round(x, int(n - math.ceil(math.log10(abs(x)))))

    @staticmethod
    def time_string(seconds):
        """Returns time in seconds as a string formatted HHHH:MM:SS."""
        s = int(round(seconds))  # round to nearest second
        h, s = divmod(s, 3600)   # get hours and remainder
        m, s = divmod(s, 60)     # split remainder into minutes and seconds
        return '%4i:%02i:%02i' % (h, m, s)

    def save_state(self, fname=None):
        """Saves state
        """
        if not fname:
            date = datetime.datetime.now().isoformat().split(".")[0]
            fname = date + "_loss_" + str(self.get_loss()) + ".state"
        print("Saving state to: %s" % fname)
        with open(fname, "w") as fh:
            pickle.dump(self.state, fh)

    def move(self, state):
        """Create a state change
        """
        move_step = np.random.rand(len(state)) * 2. - 1.
        move_step *= 0.0005
        for _ in range(len(state)):
            state[_] = state[_] * (1 + move_step[_])
        return state

    def get_loss(self, state):
        """Calculate state's loss
        """
        lossfxn = \
            self.calc.model.lossfunction.get_loss(np.array(state),
                                                  lossprime=False,)['loss']
        return lossfxn

    def set_user_exit(self, signum, frame):
        """Raises the user_exit flag, further iterations are stopped
        """
        self.user_exit = True

    def set_schedule(self, schedule):
        """Takes the output from `auto` and sets the attributes
        """
        self.Tmax = schedule['tmax']
        self.Tmin = schedule['tmin']
        self.steps = int(schedule['steps'])

    def copy_state(self, state):
        """Returns an exact copy of the provided state Implemented according to
        self.copy_strategy, one of

        * deepcopy : use copy.deepcopy (slow but reliable)
        * slice: use list slices (faster but only works if state is list-like)
        * method: use the state's copy() method
        """
        if self.copy_strategy == 'deepcopy':
            return copy.deepcopy(state)
        elif self.copy_strategy == 'slice':
            return state[:]
        elif self.copy_strategy == 'copy':
            return state.copy()

    def update(self, step, T, L, acceptance, improvement):
        """Prints the current temperature, loss, acceptance rate, improvement
        rate, elapsed time, and remaining time.

        The acceptance rate indicates the percentage of moves since the last
        update that were accepted by the Metropolis algorithm.  It includes
        moves that decreased the loss, moves that left the loss unchanged, and
        moves that increased the loss yet were reached by thermal excitation.

        The improvement rate indicates the percentage of moves since the last
        update that strictly decreased the loss.  At high temperatures it will
        include both moves that improved the overall state and moves that
        simply undid previously accepted moves that increased the loss by
        thermal excititation.  At low temperatures it will tend toward zero as
        the moves that can decrease the loss are exhausted and moves that would
        increase the loss are no longer thermally accessible.
        """

        elapsed = time.time() - self.start
        if step == 0:
            self.calc._log('\n')
            header = ' %5s %12s %12s %7s %7s %10s %10s'
            self.calc._log(header % ('Step', 'Temperature', 'Loss (SSD)',
                                     'Accept', 'Improve', 'Elapsed',
                                     'Remaining'))
            self.calc._log(header % ('=' * 5, '=' * 12, '=' * 12,
                                     '=' * 7, '=' * 7, '=' * 10,
                                     '=' * 10,))
            self.calc._log(
                    ' %5i %12.2e %12.4e                   %s            '
                    % (step, T, L, self.time_string(elapsed)))
        else:
            remain = (self.steps - step) * (elapsed / step)
            self.calc._log(' %5i %12.2e %12.4e %7.2f%% %7.2f%% %s %s' %
                           (step, T, L,
                            100.0 * acceptance, 100.0 * improvement,
                            self.time_string(elapsed),
                            self.time_string(remain)))

    def anneal(self):
        """Minimizes the loss of a system by simulated annealing.

        Parameters
        ---------
        state
            An initial arrangement of the system

        Returns
        -------
        state, loss
            The best state and loss found.
        """
        step = 0
        self.start = time.time()

        # Precompute factor for exponential cooling from Tmax to Tmin
        if self.Tmin <= 0.0:
            raise Exception('Exponential cooling requires a minimum "\
                "temperature greater than zero.')
        Tfactor = -math.log(self.Tmax / self.Tmin)

        # Note initial state
        T = self.Tmax
        L = self.get_loss(self.state)
        prevState = self.copy_state(self.state)
        prevLoss = L
        bestState = self.copy_state(self.state)
        bestLoss = L
        trials, accepts, improves = 0, 0, 0
        if self.updates > 0:
            updateWavelength = self.steps / self.updates
            self.update(step, T, L, None, None)

        # Attempt moves to new states
        while step < (self.steps - 1) and not self.user_exit:
            step += 1
            T = self.Tmax * math.exp(Tfactor * step / self.steps)
            self.state = self.move(self.state)
            L = self.get_loss(self.state)
            dL = L - prevLoss
            trials += 1
            if dL > 0.0 and math.exp(-dL / T) < random.random():
                # Restore previous state
                self.state = self.copy_state(prevState)
                L = prevLoss
            else:
                # Accept new state and compare to best state
                accepts += 1
                if dL < 0.0:
                    improves += 1
                prevState = self.copy_state(self.state)
                prevLoss = L
                if L < bestLoss:
                    bestState = self.copy_state(self.state)
                    bestLoss = L
            if self.updates > 1:
                if step // updateWavelength > (step - 1) // updateWavelength:
                    self.update(
                        step, T, L, accepts / trials, improves / trials)
                    trials, accepts, improves = 0, 0, 0

        # line break after progress output
        print('')

        self.state = self.copy_state(bestState)
        if self.save_state_on_exit:
            self.save_state()
        # Return best state and loss
        return bestState, bestLoss

    def auto(self, minutes, steps=2000):
        """Minimizes the loss of a system by simulated annealing with automatic
        selection of the temperature schedule.

        Keyword arguments:
        state -- an initial arrangement of the system
        minutes -- time to spend annealing (after exploring temperatures)
        steps -- number of steps to spend on each stage of exploration

        Returns the best state and loss found.
        """

        def run(T, steps):
            """Anneals a system at constant temperature and returns the state,
            loss, rate of acceptance, and rate of improvement.
            """
            L = self.get_loss()
            prevState = self.copy_state(self.state)
            prevLoss = L
            accepts, improves = 0, 0
            for step in range(steps):
                self.move()
                L = self.get_loss()
                dL = L - prevLoss
                if dL > 0.0 and math.exp(-dL / T) < random.random():
                    self.state = self.copy_state(prevState)
                    L = prevLoss
                else:
                    accepts += 1
                    if dL < 0.0:
                        improves += 1
                    prevState = self.copy_state(self.state)
                    prevLoss = L
            return L, float(accepts) / steps, float(improves) / steps

        step = 0
        self.start = time.time()

        # Attempting automatic simulated anneal...
        # Find an initial guess for temperature
        T = 0.0
        L = self.get_loss()
        self.update(step, T, L, None, None)
        while T == 0.0:
            step += 1
            self.move()
            T = abs(self.get_loss() - L)

        # Search for Tmax - a temperature that gives 98% acceptance
        L, acceptance, improvement = run(T, steps)

        step += steps
        while acceptance > 0.98:
            T = self.round_figures(T / 1.5, 2)
            L, acceptance, improvement = run(T, steps)
            step += steps
            self.update(step, T, L, acceptance, improvement)
        while acceptance < 0.98:
            T = self.round_figures(T * 1.5, 2)
            L, acceptance, improvement = run(T, steps)
            step += steps
            self.update(step, T, L, acceptance, improvement)
        Tmax = T

        # Search for Tmin - a temperature that gives 0% improvement
        while improvement > 0.0:
            T = self.round_figures(T / 1.5, 2)
            L, acceptance, improvement = run(T, steps)
            step += steps
            self.update(step, T, L, acceptance, improvement)
        Tmin = T

        # Calculate anneal duration
        elapsed = time.time() - self.start
        duration = self.round_figures(int(60.0 * minutes * step / elapsed), 2)

        print('')  # New line after auto() output
        # Don't perform anneal, just return params
        return {'tmax': Tmax, 'tmin': Tmin, 'steps': duration}


class MetaDict(dict):
    """Dictionary that can also store metadata. Useful for images dictionary
    so that images can still be iterated by keys.
    """
    metadata = {}
