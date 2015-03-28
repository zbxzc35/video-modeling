# User configurations:
data_root = '../data/bouncing_balls/1balls/' 
image_suffix = '.jpeg'
image_shape = (16, 16) # single channel images
trainframes = 5000
testframes = 1000
numframes = 5

# Paramters according to user configurations:
frame_len = image_shape[0] * image_shape[1] # single channel images
seq_len = frame_len * numframes

features_root = 'features/'


# MODEL PARAMETERS 
lr = 1e2 # learning rate
save_epoch = 100
models_root = 'models/'
batch_size = 1
hidden_size = 50
