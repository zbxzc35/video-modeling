import numpy, pylab
import theano
import theano.tensor as T
from theano.tensor.shared_randomstreams import RandomStreams
from params import Params

class GatedAutoencoder(Params):
    """
    Factored Gated Autoencoder
    """
    def __init__(self, 
                    dimdat, dimfac, dimmap,
                    wdf_left=None, wdf_right=None, wfm=None,
                    bd=None, bm=None,
                    output_type='real', corrupt_type='none', corrupt_level=0.0, 
                    numpy_rng=None, theano_rng=None,
                    name=''):
        """
        name : string type name of the model
        # mode : if 'reconstruct' then train for two-way reconstruction
        #         if 'up' then infer mapping unit using two input data
        #         # if 'left' then predict left using right and mapping unit
        #         if 'right' then predict right using left and mapping unit
        """
        self.name = name

        if not numpy_rng:  
            self.numpy_rng = numpy.random.RandomState(1) 
        else:
            self.numpy_rng = numpy_rng
        if not theano_rng:  
            self.theano_rng = RandomStreams(1)

        # hyper parameters
        ########################################################################
        """
        dimdat : Dimension of the data
        dimfac : Dimension of the factors
        dimmap : Dimension of the mapping units
        """
        self.dimdat = dimdat
        self.dimfac = dimfac
        self.dimmap = dimmap

        self.output_type = output_type
        self.corrupt_type = corrupt_type
        self.corrupt_level = corrupt_level

        # trainable parameters
        ########################################################################
        """
        wdf_left :
        wdf_right :
        wfm :
        bd :
        bm :
        """
        #
        if wdf_left == None:
            self.wdf_left = self.init_param(size=(dimdat, dimfac), scale=.01,  
                                        mode='n', name=self.name+':wdf_left')
        else:
            self.wdf_left = wdf_left
        #
        if wdf_right == None:
            self.wdf_right = self.init_param(size=(dimdat, dimfac), scale=.01,  
                                        mode='n', name=self.name+':wdf_right')
        else:
            self.wdf_right = wdf_right
        #
        if wfm == None:
            self.wfm = self.init_param(size=(dimfac, dimmap), scale=.01,  
                                        mode='n', name=self.name+':wfm')
        else:
            self.wfm = wfm
        #
        if bd == None:
            self.bd = self.init_param(size=(dimdat), scale=0.,  
                                        mode='r', name=self.name+':bd')
        else:
            self.bd = bd
        #
        if bm == None:
            self.bm = self.init_param(size=(dimmap), scale=0.,  
                                        mode='r', name=self.name+':bm')
        else:
            self.bm = bm

        self.params =[self.wdf_left, self.wdf_right, self.wfm, self.bd, self.bm]

        # layers 
        ########################################################################
        """
        dat_left : 
        dat_right :
        fac_left :
        fac_right :
        map ::
        """
        
        self.inputs = T.matrix(name=self.name+':inputs') 
        dat_left = self.inputs[:, :dimdat] 
        dat_right = self.inputs[:, dimdat:] 

        if corrupt_type != None:
            dat_left = self.corrupt(dat_left, 
                        self.corrupt_type, self.corrupt_level)
            dat_right = self.corrupt(dat_right, 
                        self.corrupt_type, self.corrupt_level)
            
        fac_left = T.dot(dat_left, self.wdf_left)
        fac_right = T.dot(dat_right, self.wdf_right)
        map = self.fac_infer(fac_left, fac_right)
        fac_map = T.dot(map, self.wfm)
        recons_left = self.fac_predict(fac_right, fac_map, 'l')
        recons_right = self.fac_predict(fac_left, fac_map, 'r')
        recons = T.concatenate((recons_left, recons_right), axis=1)
        cost = T.mean((recons_left - self.inputs[:, :dimdat])**2 +\
                            (recons_right - self.inputs[:, dimdat:])**2)
        grads = T.grad(cost, self.params) 
        self.cost = cost 
        self.grads = grads 
        # functions
        self.f_map = theano.function([self.inputs], map)
        self.f_recons = theano.function([self.inputs], recons)
        self.f_cost = theano.function([self.inputs], cost)
        self.f_grads = theano.function([self.inputs], grads)

    def corrupt(self, raw, corrupt_type, corrupt_level):
        if corrupt_type == 'none' or corrupt_type == None:
            corrupted = raw
        elif corrupt_type == 'zeromask':
            corrupted = self.theano_rng.binomial(size=raw.shape, 
                n=1, p=1.0-corrupt_level, 
                dtype=theano.config.floatX) * raw
        elif corrupt_type == 'mixedmask':
            corrupted = self.theano_rng.binomial(size=raw.shape, 
                n=1, p=1.0-corrupt_level/2, 
                dtype=theano.config.floatX) * raw
            corrupted = (1-self.theano_rng.binomial(size=corrupted.shape, 
                n=1, p=1.0-corrupt_level/2, 
                dtype=theano.config.floatX)) * corrupted
        elif corrupt_type == 'gaussian':
            corrupted = self.theano_rng.normal(size=raw.shape, avg=0.0, 
            std=corrupt_level, dtype=theano.config.floatX) + raw
        else:
            assert False, "corrupt type not understood"
        return corrupted

    def fac_infer(self, fac_left, fac_right):
        """
        Infer the mapping unit given the left and right factors. 
        """
        map = self._fac_infer(fac_left, fac_right, self.wfm, self.bm)
        return map

    def fac_predict(self, fac_in, fac_map, dir='r'):
        """
        Predict one of the data given the factor of the other data and the 
        mapping unit.

        Parameters
        ----------
        dir: str
            Direction of the prediction, 'l' for left and 'r' for right.
        """
        if dir == 'l':
            wdf_out = self.wdf_left
        else:
            wdf_out = self.wdf_right
        dat_out = self._fac_predict(fac_in, fac_map, wdf_out, self.bd)
        return dat_out

    def infer(self, dat_left, dat_right):
        """
        Infer the mapping unit given the left and right data. 
        """
        map = self._infer(dat_left, dat_right, 
                            self.wdf_left, self. wdf_right, self.wfm, self.bm)
        return map

    def predict(self, dat_in, map, dir='r'):
        """
        Predict one of the data given the another data and the mapping unit.

        Parameters
        ----------
        dir: str
            Direction of the prediction, 'l' for left and 'r' for right.
        """
        if dir == 'l':
            wdf_in = self.wdf_right
            wdf_out = self.wdf_left
        else:
            wdf_in = self.wdf_left
            wdf_out = self.wdf_right
        dat_out = self._fac_predict(dat_in, map, 
                                    wdf_in, wdf_out, self.wfm, self.bd)
        return dat_out

    def _fac_infer(self, fac_left, fac_right, wfm, bm):
        "Called by self.fac_infer()."
        premap = T.dot(fac_left * fac_right, wfm.T) + bm
        map = T.nnet.sigmoid(premap)
        return map

    def _fac_predict(self, fac_in, fac_map, wdf_out, bd):
        "Called by self.predict()."
        dat_out = T.dot(fac_in * fac_map, wdf_out) + bd
        return dat_out

    def _infer(self, dat_left, dat_right, wdf_left, wdf_right, wfm, bm):
        "Called by self.infer()."
        fac_left = T.dot(dat_left, wdf_left)
        fac_right = T.dot(dat_right, wdf_right)
        # premap = T.dot(fac_left * fac_right, wfm.T) + bm
        # map = T.nnet.sigmoid(premap)
        map = self._fac_infer(fac_left, fac_right, wfm, bm)
        return map

    def _predict(self, dat_in, map, wdf_in, wdf_out, wfm, bd):
        "Called by self.predict()."
        fac_in = T.dot(dat_in, wdf_in.T)
        fac_map = T.dot(map, wfm)
        # dat_out = T.dot(fac_in * fac_map, wdf_out) + bd
        dat_out = self._fac_predict(fac_in, fac_map, wdf_out, bd)
        return dat_out

    def normalize_filters(self):
        """
        Normalize filters. 
        """
        raise Exception('Not impleted yet. ')


