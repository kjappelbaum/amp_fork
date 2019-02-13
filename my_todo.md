# Kevin's ToDo list for AMP

- [ ] Maybe write a Keras module: Can use both Tensorflow and PyTorch as backend, GPU acceleration and
 more complex architectures, but not limited to one Tensorflow version (Keras API changes less frequently). 
 Look here into the TF implementation and copy good stuff there. Offer learning rate cycling, dropout, early stopping, 
 Would allow to use Tensorboard to monitor training. 
 AdaNet to automatically find best architecture 
- [ ] Add maybe option to read from `.yaml` input files to make it a bit easier to use (i.e. input file that specifies
structures and settings and don't have to write python. We could also have tool/flask app to create this input file)
- [ ] Update docs
- [ ] Increase test coverage `lint` and `yapf` the code. Use Travis for automatic testing. 
- [ ] Optimize training sampling strategies? 
- [ ] [SWAG](https://arxiv.org/pdf/1902.02476.pdf) as alternative to bootstrapping
- [ ] Add tools to analyze network, visualize hidden layers. 
- [ ] Create Docker image for quick development, testing and deployment of AMP