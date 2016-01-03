"""
This script creates a list of three images. It then calculates behler-neural
scheme forces and energies of different combinations of them with and without
fortran modules, and check consistency between them.

"""

###############################################################################

import numpy as np
from ase import Atoms
from amp import Amp
from amp.descriptor import Behler
from amp.regression import NeuralNetwork

###############################################################################
# Making the list of images


def make_images():
    """Makes test images."""

    images = [Atoms(symbols='Pd4O2',
                    pbc=np.array([True,  True, False], dtype=bool),
                    cell=np.array(
                        [[7.78,   0.,   0.],
                         [0.,   5.50129076,   0.],
                            [0.,   0.,  15.37532269]]),
                    positions=np.array(
                        [[0.,  0.,  8.37532269],
                            [3.89,  0.,  8.37532269],
                            [0.,  2.75064538,  8.37532269],
                            [3.89,  2.75064538,  8.37532269],
                            [5.835,  1.37532269,  8.5],
                            [5.835,  7.12596807,  8.]])),
              Atoms(symbols='Pd4O2',
                    pbc=np.array([True,  True, False], dtype=bool),
                    cell=np.array(
                        [[7.78,   0.,   0.],
                         [0.,   5.50129076,   0.],
                            [0.,   0.,  15.37532269]]),
                    positions=np.array(
                        [[8.43409903e-03,  -4.40430259e-03,
                          8.37107726e+00],
                            [3.88430768e+00,   5.28005966e-03,
                                8.36678641e+00],
                            [-1.01122240e-02,   2.74577426e+00,
                                8.37861758e+00],
                            [3.88251383e+00,   2.74138906e+00,
                                8.37087611e+00],
                            [5.82067191e+00,   1.19156898e+00,
                                8.97714483e+00],
                            [5.83355445e+00,   7.53318593e+00,
                             8.50142020e+00]])),
              Atoms(symbols='Pd4O2',
                    pbc=np.array([True,  True, False], dtype=bool),
                    cell=np.array(
                        [[7.78,   0.,   0.],
                         [0.,   5.50129076,   0.],
                            [0.,   0.,  15.37532269]]),
                    positions=np.array(
                        [[1.84507759e-02,  -9.96620379e-03,
                          8.36465110e+00],
                            [3.87691266e+00,   9.29708987e-03,
                                8.35604207e+00],
                            [-1.29700138e-02,   2.74373753e+00,
                                8.37941484e+00],
                            [3.86813484e+00,   2.73488653e+00,
                                8.36395999e+00],
                            [5.80386111e+00,   7.98192190e-01,
                                9.74324179e+00],
                            [5.83223956e+00,   8.23855393e+00,
                             9.18295137e+00]]))]

    return images

###############################################################################
# Parameters

cutoff = 6.5
activation = 'tanh'
hiddenlayers = {'O': (5, 5), 'Pd': (5, 5)}

Gs = {'O': [{'eta': 0.05, 'type': 'G2', 'element': 'O'},
            {'eta': 0.05, 'type': 'G2', 'element': 'Pd'},
            {'eta': 2.0, 'type': 'G2', 'element': 'O'},
            {'eta': 2.0, 'type': 'G2', 'element': 'Pd'},
            {'eta': 4.0, 'type': 'G2', 'element': 'O'},
            {'eta': 4.0, 'type': 'G2', 'element': 'Pd'},
            {'eta': 8.0, 'type': 'G2', 'element': 'O'},
            {"eta": 8.0, "type": "G2", "element": "Pd"},
            {"eta": 20.0, "type": "G2", "element": "O"},
            {"eta": 20.0, "type": "G2", "element": "Pd"},
            {"eta": 40.0, "type": "G2", "element": "O"},
            {"eta": 40.0, "type": "G2", "element": "Pd"},
            {"eta": 80.0, "type": "G2", "element": "O"},
            {"eta": 80.0, "type": "G2", "element": "Pd"},
            {"zeta": 1.0, "elements": ["O", "O"], "type": "G4", "gamma": 1.0,
             "eta": 0.005},
            {"zeta": 1.0, "elements": ["O", "Pd"], "type": "G4", "gamma": 1.0,
             "eta": 0.005},
            {"zeta": 1.0, "elements": ["Pd", "Pd"], "type": "G4",
             "gamma": 1.0, "eta": 0.005},
            {"zeta": 1.0, "elements": ["O", "O"],
             "type": "G4", "gamma": -1.0, "eta": 0.005},
            {"zeta": 1.0, "elements": ["O", "Pd"],
             "type": "G4", "gamma": -1.0, "eta": 0.005},
            {"zeta": 1.0, "elements": ["Pd", "Pd"], "type": "G4",
             "gamma": -1.0,
             "eta": 0.005}, {"zeta": 2.0, "elements": ["O", "O"], "type": "G4",
                             "gamma": 1.0, "eta": 0.005},
            {"zeta": 2.0, "elements": ["O", "Pd"],
             "type": "G4", "gamma": 1.0, "eta": 0.005},
            {"zeta": 2.0,
             "elements": ["Pd", "Pd"], "type": "G4",
             "gamma": 1.0, "eta": 0.005},
            {"zeta": 2.0, "elements": ["O", "O"], "type": "G4", "gamma": -1.0,
             "eta": 0.005},
            {"zeta": 2.0, "elements": ["O", "Pd"], "type": "G4",
             "gamma": -1.0, "eta": 0.005}, {"zeta": 2.0,
                                            "elements": ["Pd", "Pd"],
                                            "type": "G4", "gamma": -1.0,
                                            "eta": 0.005},
            {"zeta": 4.0,
             "elements": ["O", "O"],
             "type": "G4",
             "gamma": 1.0, "eta": 0.005},
            {"zeta": 4.0, "elements": ["O", "Pd"], "type": "G4", "gamma": 1.0,
             "eta": 0.005}, {"zeta": 4.0, "elements": ["Pd", "Pd"],
                             "type": "G4", "gamma": 1.0, "eta": 0.005},
            {"zeta": 4.0, "elements": ["O", "O"], "type": "G4", "gamma": -1.0,
             "eta": 0.005}, {"zeta": 4.0, "elements": ["O", "Pd"],
                             "type": "G4", "gamma": -1.0, "eta": 0.005},
            {"zeta": 4.0, "elements": ["Pd", "Pd"],
             "type": "G4", "gamma": -1.0,
             "eta": 0.005}],
      "Pd": [{"eta": 0.05, "type": "G2", "element": "O"},
             {"eta": 0.05, "type": "G2", "element": "Pd"},
             {"eta": 2.0, "type": "G2", "element": "O"},
             {"eta": 2.0, "type": "G2", "element": "Pd"},
             {"eta": 4.0, "type": "G2", "element": "O"},
             {"eta": 4.0, "type": "G2", "element": "Pd"},
             {"eta": 8.0, "type": "G2", "element": "O"},
             {"eta": 8.0, "type": "G2", "element": "Pd"},
             {"eta": 20.0, "type": "G2", "element": "O"},
             {"eta": 20.0, "type": "G2", "element": "Pd"},
             {"eta": 40.0, "type": "G2", "element": "O"},
             {"eta": 40.0, "type": "G2", "element": "Pd"},
             {"eta": 80.0, "type": "G2", "element": "O"},
             {"eta": 80.0, "type": "G2", "element": "Pd"},
             {"zeta": 1.0, "elements": ["O", "O"], "type": "G4", "gamma": 1.0,
              "eta": 0.005},
             {"zeta": 1.0, "elements": ["O", "Pd"], "type": "G4", "gamma": 1.0,
              "eta": 0.005}, {"zeta": 1.0,
                              "elements": ["Pd", "Pd"],
                              "type": "G4",
                              "gamma": 1.0, "eta": 0.005},
             {"zeta": 1.0, "elements": ["O", "O"], "type": "G4",
              "gamma": -1.0, "eta": 0.005}, {"zeta": 1.0,
                                             "elements": ["O", "Pd"],
                                             "type": "G4", "gamma": -1.0,
                                             "eta": 0.005},
             {"zeta": 1.0, "elements": ["Pd", "Pd"], "type": "G4",
              "gamma": -1.0,
              "eta": 0.005}, {"zeta": 2.0, "elements": ["O", "O"],
                              "type": "G4",
                              "gamma": 1.0, "eta": 0.005},
             {"zeta": 2.0,
              "elements": ["O", "Pd"], "type": "G4",
              "gamma": 1.0, "eta": 0.005}, {"zeta": 2.0,
                                            "elements": ["Pd", "Pd"],
                                            "type": "G4",
                                            "gamma": 1.0, "eta": 0.005},
             {"zeta": 2.0, "elements": ["O", "O"], "type": "G4", "gamma": -1.0,
              "eta": 0.005}, {"zeta": 2.0, "elements": ["O", "Pd"],
                              "type": "G4",
                              "gamma": -1.0, "eta": 0.005},
             {"zeta": 2.0, "elements": ["Pd", "Pd"],
              "type": "G4", "gamma": -1.0, "eta": 0.005},
             {"zeta": 4.0, "elements": ["O", "O"],
              "type": "G4", "gamma": 1.0, "eta": 0.005},
             {"zeta": 4.0, "elements": ["O", "Pd"], "type": "G4", "gamma": 1.0,
              "eta": 0.005}, {"zeta": 4.0, "elements": ["Pd", "Pd"],
                              "type": "G4",
                              "gamma": 1.0, "eta": 0.005},
             {"zeta": 4.0,
              "elements": ["O", "O"],
              "type": "G4", "gamma": -1.0, "eta": 0.005},
             {"zeta": 4.0, "elements": ["O", "Pd"],
              "type": "G4", "gamma": -1.0, "eta": 0.005},
             {"zeta": 4.0, "elements": ["Pd", "Pd"], "type": "G4",
              "gamma": -1.0,
              "eta": 0.005}]}

fingerprints_range = {"O": [[1.2034320541645842, 1.2325033032109112],
                            [6.126415779807456, 6.978993471872114],
                            [0.9968712422847974, 1.0238339591857768],
                            [3.8381486000216656, 4.6059867092450295],
                            [0.895627825206874, 0.9671954702902308],
                            [2.583663009213816, 3.2975746566094606],
                            [0.7964913272920149, 0.9263856740488036],
                            [1.3358420027866575, 1.987698731796872],
                            [0.6086945405610695, 0.8469928578399282],
                            [0.2529142293461268, 0.7771634549572402],
                            [0.3914378098148111, 0.7306361163848886],
                            [0.020116896658220102, 0.35759863784953067],
                            [0.16188160578588526, 0.5436809953654286],
                            [0.00018177869062004963, 0.12577780799256955],
                            [2.9283890234835495, 2.960848034649544],
                            [30.849062520667466, 34.34079115772228],
                            [74.38292698900159, 81.77213709053859],
                            [1.6948136646289693, 1.803559109943061],
                            [20.032647223918715, 25.204662559464523],
                            [46.30668067734771, 58.99262463422656],
                            [2.37554239540103, 2.7402971203873707],
                            [21.915472638677855, 25.585727302527907],
                            [54.57445823130601, 61.34907477324089],
                            [1.109508025380456, 1.6154672068468818],
                            [11.916848644888729, 17.04495978743268],
                            [27.88887260037905, 39.18415587653102],
                            [1.8928302257282086, 2.5827385383035284],
                            [14.565545948279196, 17.941552668205755],
                            [36.94672253980532, 42.672289485060745],
                            [0.6553641770222022, 1.4212816597490932],
                            [6.00446500499159, 10.95563925572871],
                            [15.456097104319266, 24.846009591495683]],
                      "Pd": [[0.8893801678132963, 2.186742268993366],
                             [5.681935730435191, 5.801357868163544],
                             [0.28325235730086895, 1.7195167772827762],
                             [3.319274384132528, 3.4278827090091513],
                             [0.08915750058756017, 1.5653576140941878],
                             [2.053165118375831, 2.1493466057807606],
                             [0.009285644347874652, 1.3396267483639697],
                             [0.8813449647319378, 0.949755776664418],
                             [1.4022708468796206e-05, 0.8694356341233072],
                             [0.08961848129998626, 0.10519747021560875],
                             [2.5350651988745783e-10, 0.4474694168207284],
                             [0.002199096348873827, 0.002942664869970825],
                             [1.3547037121993997e-19, 0.13803579787982578],
                             [1.3829812001140997e-06, 2.3283471452833342e-06],
                             [2.245260381205755, 6.506711057752208],
                             [30.80688145836148, 46.62802877467697],
                             [63.159691665137835, 63.42318872782115],
                             [1.4470182218367846, 3.5407788975262466],
                             [16.920091949041364, 27.974461180856085],
                             [43.372163387951744, 45.106267442742194],
                             [2.1007039650495236, 5.235507846017004],
                             [24.98117242089699, 38.28678610359639],
                             [47.903805932396644, 48.16729306561395],
                             [0.8039272162816901, 2.5404648021947756],
                             [11.094382911576862, 19.43921017240714],
                             [28.14489163971961, 29.853649179126506],
                             [2.0677437396917027, 3.980577524358615],
                             [18.507476335936385, 30.408978128204563],
                             [33.915660566694726, 34.201570710274964],
                             [0.2569160731561561, 1.5411619576089908],
                             [4.8043897598894185, 13.387133883397796],
                             [17.225764659147405, 18.83859512207448]]}

weights = {"O": {1: np.matrix([[0.00036942165470836563, 0.022852891328080965,
                                -0.007763989520407272, 0.0017904084613678817,
                                -0.04680830976127531],
                               [-0.011220619170475267, -0.031465481900468384,
                                -0.0185587250581268, 0.00029876794872765733,
                                -0.03270538302430687],
                               [0.009269384571647388, -0.004439491584362951,
                                0.02041622613407708, -0.04075220241750707,
                                -0.004384443250886716],
                               [-0.02045226889653854, -0.04085271674587569,
                                -0.0007470148939682439, 0.017448937916376722,
                                -0.03247360282480993],
                               [0.014076539841285075, -0.0006001148651055555,
                                -0.011206188631385075, 0.036131770356541804,
                                0.04019195568663911], [0.04438555375359607,
                                                       -0.03630318854778723, -
                                                       0.011787189723001579,
                                                       0.03403384156560013,
                                                       0.015653363757362176],
                               [0.02134038436971622, 0.000554719592425923,
                                -0.04353602059838731, 0.02829112575071807,
                                -0.010315738192632054],
                               [-0.009864186941597866, 0.025867111325423034,
                                -0.030222981254973712, -0.009255262808615411,
                                -0.0047940678082599025],
                               [0.009775595855839286, -0.004398102065676125,
                                -0.00195136837351699, -0.0015883410280669308,
                                0.03528054083271703],
                               [0.0088457892425432, -0.0017778202887624855,
                                -0.030182606288789264, 0.03153096931177092,
                                -0.02709527292127762], [-0.02911935923819357,
                                                        -0.011844856703362105,
                                                        0.03358589444051113,
                                                        0.007149386960731488,
                                                        -0.007590532737964187],
                               [-0.03944400124516653, 0.03562647918045643,
                                -0.041584201666104756, -0.03482985747462908,
                                -0.045374395214468496],
                               [0.019057890033725933, -0.012580031773554046,
                                0.04290707878850142, 0.04177600131985214,
                                -0.03500384259370384],
                               [-0.02033084113684249, -0.01111345650394805,
                                -0.005485434669132497, 0.03554246348547074,
                                0.031421467582530324],
                               [-0.03310168568774624, 0.04617363212275834,
                                0.03868456178440169, 0.012151585419746959,
                                -0.007359447003748548],
                               [0.044255356329426065, 0.036122120043098505,
                                0.001842950538131695, -0.01615761183192349,
                                -0.03771427943410247],
                               [-0.0381118034639101, -0.04643318160382238,
                                0.02900519652241655, -0.008475138348622263,
                                0.021893066028991853],
                               [0.016038314042298385, 0.03545540262812917,
                                -0.031220884269865096, -0.033670838618425646,
                                0.04684810506588663],
                               [0.037697271308168634, -0.04250612661317486,
                                0.0028173761257807364, 0.04503591051281573,
                                -0.005888259820159045],
                               [-0.01688674535740177, 0.03765441774468983,
                                0.040162723331136185, 0.023291060425779497,
                                0.01875483057892434],
                               [0.009559969717541077, -0.010986361005406543,
                                0.017717618257908102, 0.021594452542040676,
                                0.00668490554203105],
                               [0.02899572788647327, 0.03884753546552183,
                                0.0334345646492913, -0.0009724588802520473,
                                0.008901825903656319],
                               [0.04472782971579241, 0.020125743534124996,
                                0.018466622131502394, 0.014248370483492187,
                                0.02954224116911444],
                               [0.018038582886592464, 0.007882237781735343,
                                -0.005639481686277245, -0.030317048204748388,
                                0.011443284253329196],
                               [-0.014574589075944028, 0.027312879897418138,
                                -0.0052516221359138054, -0.02858166510190807,
                                -0.0218508786228111],
                               [-0.019062166466149163, -0.0421343628780219,
                                -0.0292511219030615, -0.04063165343284807,
                                -0.026551753085291934],
                               [-0.006973189792228912, 0.018725587327618767,
                                0.037936857142053707, 0.011375377365914208,
                                -0.03823975980860963],
                               [-0.03087795180506949, -0.002166181826768615,
                                -0.009411940441267343, 0.008062289773496219,
                                0.03143133615872179],
                               [0.022767389458292583, -0.032719990839286985,
                                0.010234126834754581, -0.0025988597425086815,
                                0.012893424785935387],
                               [0.03729503214821439, -0.04055234881977389,
                                -0.033180455803208164, -0.003962067731434399,
                                -0.04089277483943934],
                               [-0.005215540749534078, 0.013163002568367034,
                                0.03980552568163612, 0.00803385354609431,
                                7.658166702390057e-05],
                               [0.013936695364567375, 0.017657437899754047,
                                0.027548202328624413, -0.0008692880197060243,
                                0.032762776542753225],
                               [0.0, 0.0, 0.0, 0.0, 0.0]]),
                 2: np.matrix([[-0.13315704861614908, 0.21616481887190436,
                                0.07102546888848049, -0.2758348650926486,
                                -0.12434812671933795], [-0.024314957289090222,
                                                        -0.16392515185308187,
                                                        0.2058922926890992,
                                                        0.2154935160814611,
                                                        0.11014812360618259],
                               [-0.08133895309316427, -0.1937923029504461,
                                0.206977413616443, 0.03575405386811248,
                                -0.10559013113242327],
                               [0.1469937256217183, 0.07621742865022896,
                                0.08882575726900893, -0.2577928927812111,
                                0.2670748892517893],
                               [-0.141370342762172, -0.23738939477247786,
                                -0.06633785630500305, -0.24779722808875726,
                                0.17677488447247947],
                               [0.0, 0.0, 0.0, 0.0, 0.0]]),
                 3: np.matrix([[0.0377280558085506], [0.013842778159018243],
                               [-0.29408570195900635],
                               [0.19529036441834974], [-0.16745509851929688],
                               [0.0]])},
           "Pd": {1: np.matrix([[0.008070279669324429, -0.04006333630883027,
                                 -0.04312742429320118,
                                 -0.03942171198922403, -0.04540662900302544],
                                [0.01339814716182161, -0.022961503636403632,
                                 -0.006969046155031772, 0.01539617792272549,
                                 -0.02587844848147742],
                                [0.045033334892680674, 0.0034430687137840393,
                                 0.02405223418836909, -0.035506042140031155,
                                 0.021328894351546446],
                                [-0.04416667286322164, -0.03993519399665675,
                                 0.032311654583997304, -0.03745738975064494,
                                 0.006061355326268905],
                                [-0.043438846516273555, 0.020424466564239616,
                                 -0.03712722505187403, -0.04417848105963802,
                                 -0.008777813735156417],
                                [0.03965347387678732, -0.01799472378269024,
                                 0.0362866746012956, 0.009704740166992,
                                 0.0004118619760827419],
                                [-0.03180969154106336, -0.006918591959222585,
                                 0.014099398062742227, -0.022931651589221756,
                                 0.03148626725702887],
                                [0.04573128229126357, 0.016654751576744925,
                                 -0.028910689496630722,
                                 0.02242435838167882, -0.02783084152657823],
                                [0.030147617474449384, -0.009580788002314114,
                                 0.026913224902892594, -0.006350898911528513,
                                 -0.01580260272955647],
                                [-0.03128280563473111, -0.044359797916295726,
                                 -0.0455871021838766, -0.022323871191166217,
                                 -0.025520059574284607],
                                [-0.004213681746207731, -0.027963910926939888,
                                 -0.03734025976436221, -0.029904058599404374,
                                 -0.023362113055890702],
                                [0.03140805808988659, -0.01625862158802977,
                                 -0.012926251592534549, 0.0199950518624378,
                                 0.00017000814436556738],
                                [0.03611338398893238, -0.04064588225668243,
                                 -0.03548786885528668, -0.034119876099748085,
                                 -0.03249791207428783],
                                [0.04302813264222295, -0.031784410672976354,
                                 -0.0018505347572984332, -0.02619493567773821,
                                 -0.009963146880811465],
                                [-0.00382761556441661, 0.02051612655974898,
                                 -0.015084868592703193, 0.036644660445905974,
                                 0.024267396930057042],
                                [0.0027419126458524262, -0.01875730493117643,
                                 0.042029556463568374, -0.033491496522005004,
                                 0.04664358315093048],
                                [-0.00857053904710025, 0.004386575075249165,
                                 -0.03681921382606547, 0.024055769666913862,
                                 -0.006710822409842235],
                                [0.01600071354805395, -0.03619212782962617,
                                 -0.007657861036073181, 0.04579883161005442,
                                 -0.027272703382017247],
                                [0.024782613292205463, 0.02454697361926271,
                                 0.014219326292126383, -0.03120859763819632,
                                 0.019746899921596867],
                                [-0.008107835898640163, -0.02411112524744128,
                                 0.01680784294783398, -0.03942450668164303,
                                 -0.02148968897141828],
                                [0.006160769106771449, -0.02608742029162942,
                                 -0.03445574192255718, 0.011100495475242236,
                                 -0.011890887277678633],
                                [0.019265102424069563, -0.019510992393145597,
                                 -0.039330197040643305, 0.028930252847621296,
                                 0.04535579375056527],
                                [0.0003841258275426168, -0.03140536534416318,
                                 0.004402540856303851, -0.006596225898408456,
                                 -0.012287524451218383],
                                [0.032434589752896065,
                                 -0.038422865723774166,
                                 0.04121673691259908,
                                 0.026471126594987765,
                                 -0.045659510547159485],
                                [0.016693221128737612, 0.033475787637348264,
                                 -0.01216104367054778, -0.04682497168901334,
                                 -0.025748662607038442],
                                [-0.030035984906774393, 0.03528987279339724,
                                 0.01842649225978525, 0.013967345908646303,
                                 0.030368471307811548],
                                [-0.004245382943207754, 0.004346310546406856,
                                 0.04395403376516939, -0.03528225866346128,
                                 0.040526584371759225],
                                [-0.026240373867317947, -0.02790624801091845,
                                 0.033248579584558235, -0.03456761843589754,
                                 -0.00921953855906435],
                                [-0.04029772119462781, 0.03944849938380114,
                                 0.03367466933743388, -0.04654081205741553,
                                 -0.02559442696348037],
                                [-0.019162242379646047,
                                 -0.0074198239538341496, -0.03481645962457279,
                                 0.0023221563528588313,
                                 -0.01362951107641086],
                                [-0.04359327067093935, 0.008182459343197494,
                                 -0.004311982184810589, 0.013459029430653538,
                                 -0.02593952116632298],
                                [0.03419829018664716, -0.02909906291417496,
                                 0.0450381809975251,
                                 0.04636855435694584, 0.004474211596899327],
                                [0.0, 0.0, 0.0, 0.0, 0.0]]),
                  2: np.matrix([[0.07339646055942084, -0.22682470946032204,
                                 -0.07464451676678477, -0.21765816530655968,
                                 0.10447399748556846],
                                [-0.07339330664074986, -0.2620525555813218,
                                 -0.010761218306725495, 0.07390075065002266,
                                 0.11039186125577433],
                                [-0.17516748044584285, -0.2837828871933906,
                                 -0.02085650668287642, 0.08755824083276131,
                                 0.07220039658405131],
                                [0.23974597425595473, 0.24760019759492297,
                                 -0.22060915253115443, -0.28310518337421325,
                                 -0.016857214958102662],
                                [0.11687787432599622, -0.10151689213238121,
                                 0.18735099239621017, 0.21356695418645139,
                                 -0.240568272158666],
                                [0.0, 0.0, 0.0, 0.0, 0.0]]),
                  3: np.matrix([[0.05906457619187622], [-0.29300196568707426],
                                [-0.018802515167880285],
                                [-0.2723126668305828], [0.22668984898833738],
                                [0.0]])}}

scalings = {"O": {"intercept": 4.2468934359280288,
                  "slope": 3.1965614888424687},
            "Pd": {"intercept": 4.2468934359280288,
                   "slope": 3.1965614888424687}}

###############################################################################
# Testing pure-python and fortran versions of behler-neural force call


def test():

    images = make_images()

    for fortran in [False, True]:

        calc = Amp(descriptor=Behler(cutoff=cutoff, Gs=Gs,),
                   regression=NeuralNetwork(hiddenlayers=hiddenlayers,
                                            weights=weights,
                                            scalings=scalings,
                                            activation=activation,),
                   fingerprints_range=fingerprints_range,
                   fortran=fortran,)

        if fortran is False:
            reference_energies = [calc.get_potential_energy(image)
                                  for image in images]
        else:
            predicted_energies = [calc.get_potential_energy(image)
                                  for image in images]
            for image_no in range(len(predicted_energies)):
                assert (abs(predicted_energies[image_no] -
                            reference_energies[image_no]) < 10.**(-5.)), \
                    'Calculated energy value of image %i by \
                    fortran version is not consistent with the \
                    value of python version.' % (image_no + 1)

        if fortran is False:
            reference_forces = [calc.get_forces(image) for image in images]
        else:
            predicted_forces = [calc.get_forces(image) for image in images]

            for image_no in range(len(predicted_forces)):
                for index in range(np.shape(predicted_forces[image_no])[0]):
                    for k in range(np.shape(predicted_forces[image_no])[1]):
                        assert (abs(predicted_forces[image_no][index][k] -
                                    reference_forces[image_no][index][k]) <
                                10.**(-5.)), \
                            'Calculated %i force of atom %i of \
                            image %i by fortran version is not  \
                            consistent with the value of python \
                            version.' % (k, index, image_no + 1)

###############################################################################

if __name__ == '__main__':
    test()
