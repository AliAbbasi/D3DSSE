
#====================================================================================================================================================

# 14 category of objects    
# scene size: 84 x 44 x 84     
# focal loss
# BN layer after each layer 
# fetch random batches

#====================================================================================================================================================

import sys, glob, datetime, time, random, os, os.path, shutil, logging
import numpy            as     np
from   random           import randint
from   numpy            import array 
from   collections      import Counter
from   multiprocessing  import Pool 
import tensorflow       as     tf 
import utils # TODO fix it later

#====================================================================================================================================================

classes_count        = 14
scene_shape          = [84, 44, 84]
halfed_scene_shape   = scene_shape[2] / 2 
directory            = 'u_net_v1'
to_train             = False
to_restore           = True
show_accuracy        = True
show_accuracy_step   = 500
save_model           = True
save_model_step      = 1000
visualize_scene      = True
visualize_scene_step = 5000
subset_train         = False 
train_directory      = 'house_2/' 
test_directory       = 'test_data_2/'
max_iter             = 150000
learning_rate        = 0.00005
batch_size           = 32 
num_of_vis_batch     = 15

logging.basicConfig(filename=str(directory)+'.log', level=logging.DEBUG) 

if not os.path.exists(directory):
    os.makedirs(directory)
    
train_data = []  
test_data  = []

for item in glob.glob(train_directory + "*.npy"):
    train_data.append(item)
    
for item in glob.glob(test_directory + "*.npy"):
    test_data.append(item)

batch_threshold = 0
if subset_train:
    batch_threshold = batch_size * visualize_scene_step
else:
    batch_threshold = len(train_data)
    
#=====================================================================================================================================================

def count_params():
    "print number of trainable variables"
    size = lambda v: reduce(lambda x, y: x*y, v.get_shape().as_list())
    n = sum(size(v) for v in tf.trainable_variables())
    print "Model size: %dK" % (n/1000,)   
    
#=====================================================================================================================================================

class ConvNet(object):

    def paramsFun(self): 
        params_w = {
                    # down sample
                    'w1'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , halfed_scene_shape , 64               ], stddev = 0.01 )),  
                    'w2'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 64  , 64                              ], stddev = 0.01 )), 
                    'w3'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 64  , 128                             ], stddev = 0.01 )), 
                    'w4'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 128 , 128                             ], stddev = 0.01 )),  
                    'w5'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 128 , 256                             ], stddev = 0.01 )),  
                    'w6'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 256 , 256                             ], stddev = 0.01 )),  
                    'w7'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 256 , 512                             ], stddev = 0.01 )),   
                    'w8'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 512 , 512                             ], stddev = 0.01 )),  
                    
                    # up sample
                    'w9'   : tf.Variable(tf.truncated_normal( [ 3 , 3 , 256 , 512                             ], stddev = 0.01 )),  
                    'w10'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 512 , 256                             ], stddev = 0.01 )),  
                    'w11'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 256 , 256                             ], stddev = 0.01 )), 
                    'w12'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 128 , 256                             ], stddev = 0.01 )),   
                    'w13'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 256 , 128                             ], stddev = 0.01 )), 
                    'w14'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 128 , 128                             ], stddev = 0.01 )),  
                    'w15'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 64  , 128                             ], stddev = 0.01 )),   
                    'w16'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 128 , 64                              ], stddev = 0.01 )), 
                    'w17'  : tf.Variable(tf.truncated_normal( [ 3 , 3 , 64  , 64                              ], stddev = 0.01 )),  
                    'wOut' : tf.Variable(tf.truncated_normal( [ 1 , 1 , 64 , classes_count*halfed_scene_shape ], stddev = 0.01 ))
                   } 
        params_b = {
                    'b1'   : tf.Variable(tf.truncated_normal( [ 64                               ], stddev = 0.01 )),  
                    'b2'   : tf.Variable(tf.truncated_normal( [ 64                               ], stddev = 0.01 )),  
                    'b3'   : tf.Variable(tf.truncated_normal( [ 128                              ], stddev = 0.01 )), 
                    'b4'   : tf.Variable(tf.truncated_normal( [ 128                              ], stddev = 0.01 )), 
                    'b5'   : tf.Variable(tf.truncated_normal( [ 256                              ], stddev = 0.01 )), 
                    'b6'   : tf.Variable(tf.truncated_normal( [ 256                              ], stddev = 0.01 )), 
                    'b7'   : tf.Variable(tf.truncated_normal( [ 512                              ], stddev = 0.01 )), 
                    'b8'   : tf.Variable(tf.truncated_normal( [ 512                              ], stddev = 0.01 )), 
                    
                    'b9'   : tf.Variable(tf.truncated_normal( [ 256                              ], stddev = 0.01 )), 
                    'b10'  : tf.Variable(tf.truncated_normal( [ 256                              ], stddev = 0.01 )), 
                    'b11'  : tf.Variable(tf.truncated_normal( [ 256                              ], stddev = 0.01 )),  
                    'b12'  : tf.Variable(tf.truncated_normal( [ 128                              ], stddev = 0.01 )), 
                    'b13'  : tf.Variable(tf.truncated_normal( [ 128                              ], stddev = 0.01 )), 
                    'b14'  : tf.Variable(tf.truncated_normal( [ 128                              ], stddev = 0.01 )),  
                    'b15'  : tf.Variable(tf.truncated_normal( [ 64                               ], stddev = 0.01 )), 
                    'b16'  : tf.Variable(tf.truncated_normal( [ 64                               ], stddev = 0.01 )),  
                    'b17'  : tf.Variable(tf.truncated_normal( [ 64                               ], stddev = 0.01 )),  
                    'bOut' : tf.Variable(tf.truncated_normal( [ classes_count*halfed_scene_shape ], stddev = 0.01 ))
                   } 
                   
        return params_w,params_b

    #=================================================================================================================================================

    def scoreFun(self): 
    
        def conv2d(x, w, b, name="conv_biased", strides=1):
            with tf.name_scope(name):
                x = tf.nn.conv2d(x, w, strides=[1, strides, strides, 1], padding='SAME')
                x = tf.nn.bias_add(x, b) 
                return x  
                
        #---------------------------------------------------------------------------------------------------------------------------------------------
        
        def conv2d_transpose(x, w, b, output_shape, name="conv2d_transpose", strides=2):
            with tf.name_scope(name): 
                x = tf.nn.conv2d_transpose(x, w, output_shape=output_shape, strides=[1,strides,strides,1])
                x = tf.nn.bias_add(x, b) 
                return x 
        
        #---------------------------------------------------------------------------------------------------------------------------------------------
        
        def maxpool2d(x, k=2):
            return tf.nn.max_pool(x, ksize=[1, k, k, 1], strides=[1, k, k, 1], padding='SAME')
        
        #---------------------------------------------------------------------------------------------------------------------------------------------
        
        self.x    = tf.reshape(x, shape = [-1, scene_shape[0], scene_shape[1], halfed_scene_shape]) 
        
        #down sample
        conv_1    = tf.nn.relu(conv2d(self.x, self.params_w_['w1'], self.params_b_['b1'], "conv_1"))
        conv_2    = tf.nn.relu(conv2d(conv_1, self.params_w_['w2'], self.params_b_['b2'], "conv_2")) 
        pool_1    = maxpool2d(conv_2) 
        
        conv_3    = tf.nn.relu(conv2d(pool_1, self.params_w_['w3'], self.params_b_['b3'], "conv_3"))
        conv_4    = tf.nn.relu(conv2d(conv_3, self.params_w_['w4'], self.params_b_['b4'], "conv_4"))
        pool_2    = maxpool2d(conv_4)
        
        conv_5    = tf.nn.relu(conv2d(pool_2, self.params_w_['w5'], self.params_b_['b5'], "conv_5"))
        conv_6    = tf.nn.relu(conv2d(conv_5, self.params_w_['w6'], self.params_b_['b6'], "conv_6"))
        pool_3    = maxpool2d(conv_6)
        
        conv_7    = tf.nn.relu(conv2d(pool_3, self.params_w_['w7'], self.params_b_['b7'], "conv_7"))
        conv_8    = tf.nn.relu(conv2d(conv_7, self.params_w_['w8'], self.params_b_['b8'], "conv_8"))
        
        #up sample
        conv_9    = tf.nn.relu(conv2d_transpose(conv_8,  self.params_w_['w9'],  self.params_b_['b9'],  [batch_size, 21, 11, 256], "conv_9" ))
        concat_9  = tf.concat([conv_6, conv_9], 3)
        
        conv_10   = tf.nn.relu(conv2d(concat_9, self.params_w_['w10'], self.params_b_['b10'], "conv_10")) 
        conv_11   = tf.nn.relu(conv2d(conv_10,  self.params_w_['w11'], self.params_b_['b11'], "conv_11")) 
        
        conv_12   = tf.nn.relu(conv2d_transpose(conv_11, self.params_w_['w12'], self.params_b_['b12'], [batch_size, 42, 22, 128], "conv_12")) 
        concat_12 = tf.concat([conv_4, conv_12], 3)
        
        conv_13   = tf.nn.relu(conv2d(concat_12, self.params_w_['w13'], self.params_b_['b13'], "conv_13"))
        conv_14   = tf.nn.relu(conv2d(conv_13,   self.params_w_['w14'], self.params_b_['b14'], "conv_14"))
        
        conv_15   = tf.nn.relu(conv2d_transpose(conv_14, self.params_w_['w15'], self.params_b_['b15'], [batch_size, 84, 44, 64],  "conv_15")) 
        concat_15 = tf.concat([conv_2, conv_15], 3) 
        
        conv_16   = tf.nn.relu(conv2d(concat_15, self.params_w_['w16'], self.params_b_['b16'], "conv_16"))
        conv_17   = tf.nn.relu(conv2d(conv_16,   self.params_w_['w17'], self.params_b_['b17'], "conv_17"))
        
        conv_out  = tf.contrib.layers.flatten(conv2d(conv_17, self.params_w_['wOut'], self.params_b_['bOut'], "conv_out"))     
        
        return conv_out
        
    #---------------------------------------------------------------------------------------------------------------------------------------------------

    def costFun(self): 
        
        def focal_loss(labels, logits, gamma=2.0, alpha=4.0): 
            epsilon = 1.e-9
            labels = tf.to_int64(labels)
            labels = tf.convert_to_tensor(labels, tf.int64)
            logits = tf.convert_to_tensor(logits, tf.float32)
            num_cls = logits.shape[1]

            model_out = tf.add(logits, epsilon)
            onehot_labels = tf.one_hot(labels, num_cls)
            ce = tf.multiply(onehot_labels, -tf.log(model_out))
            weight = tf.multiply(onehot_labels, tf.pow(tf.subtract(1., model_out), gamma))
            fl = tf.multiply(alpha, tf.multiply(weight, ce))
            reduced_fl = tf.reduce_max(fl, axis=1) 
            return reduced_fl
        
        #----------------------------------------------------------------
        
        logits = tf.reshape(self.score, [-1, classes_count])
        labels = tf.reshape(self.y,     [-1               ]) 
        
        total = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=logits, labels=labels)) 
        total += tf.reduce_mean(focal_loss(labels, tf.nn.softmax(logits)))
        
        for w in self.params_w_:
            total += tf.nn.l2_loss(self.params_w_[w]) * 0.005 
            
        # penalty term
        logits       = tf.reshape(self.score, [-1, scene_shape[0], scene_shape[1], halfed_scene_shape, classes_count])
        labels       = tf.reshape(self.y,     [-1, scene_shape[0], scene_shape[1], halfed_scene_shape               ])
        split_logits = tf.split(axis=3, num_or_size_splits=halfed_scene_shape, value=logits)
        split_labels = tf.split(axis=3, num_or_size_splits=halfed_scene_shape, value=labels)
        
        for i in range(1,len(split_logits)):
            total += tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=split_logits[i], labels=split_labels[i-1]))
            
        return total
        
    #------------------------------------------------------------------------------------------------------------------------------------------------    
    
    def updateFun(self):
        return tf.train.AdamOptimizer(learning_rate = self.lr).minimize(self.cost) 
        
   #--------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__(self, x, y, lr, keepProb, phase):                    
        self.x         = x
        self.y         = y
        self.lr        = lr 
        self.keepProb  = keepProb
        self.phase     = phase 

        [self.params_w_, self.params_b_] = ConvNet.paramsFun(self) # initialization and packing the parameters
        self.score                       = ConvNet.scoreFun (self) # Computing the score function     
        self.cost                        = ConvNet.costFun  (self) # Computing the cost function 
        self.update                      = ConvNet.updateFun(self) # Computing the update function 
     
#=================================================================================================================================================== 

def accuFun(sess, trData, trLabel, batch_size):

    score   = sess.run( ConvNet_class.score , feed_dict={x: trData, keepProb: 1.0, phase: False})  
    score   = np.reshape( score,   ( batch_size, scene_shape[0], scene_shape[1], halfed_scene_shape, classes_count ) )  
    trLabel = np.reshape( trLabel, ( batch_size, scene_shape[0], scene_shape[1], halfed_scene_shape ))   
    
    totalAccuOveral   = 0.0
    totalAccuOccupied = 0.0
    
    for idxBatch in range(0, batch_size): 
        positiveOverall  = 0.0
        positiveOccupied = 0.0 
        totalOccupied    = 0.0
        
        for idx2 in range(0, scene_shape[0]):
            for idx3 in range(0, scene_shape[1]):   
                for idx4 in range(0, halfed_scene_shape):   
                    maxIdxPred = np.argmax(score[idxBatch][idx2][idx3][idx4])  
                    
                    if maxIdxPred == trLabel[idxBatch][idx2][idx3][idx4]:
                        positiveOverall+= 1.0
                        if maxIdxPred > 0:
                            positiveOccupied += 1
                            
                    if trLabel[idxBatch][idx2][idx3][idx4] > 0:
                        totalOccupied+= 1    
                    
        totalAccuOveral += (positiveOverall / (scene_shape[0] * scene_shape[1] * halfed_scene_shape * 1.0))    
        if totalOccupied == 0:
            totalOccupied = (scene_shape[0] * scene_shape[1] * halfed_scene_shape * 1.0)
        totalAccuOccupied += (positiveOccupied / totalOccupied) 
        
    totalAccuOveral   =  totalAccuOveral   / (batch_size * 1.0)
    totalAccuOccupied =  totalAccuOccupied / (batch_size * 1.0)
    
    return totalAccuOveral, totalAccuOccupied

#=================================================================================================================================================== 

def show_result(sess):  
    logging.info("Creating ply files...")
    print       ("Creating ply files...")
    
    bs = 0  
    trData, trLabel = [], [] 
    batch_arr = []
    # test_data = utils.fetch_random_batch(test_directory, batch_size)
    
    # for test in test_data:   
        # loaded_file = np.load(test)
        # batch_arr.append(utils.npy_cutter(loaded_file, scene_shape))
        # bs += 1   
        
    # batch_arr = np.reshape( batch_arr, ( bs, scene_shape[0], scene_shape[1], scene_shape[2] ))
    # trData  = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], 0:halfed_scene_shape ]               # input 
    # trLabel = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], halfed_scene_shape:scene_shape[2] ]  # gt     
    # trData  = np.reshape(trData, (-1, scene_shape[0] * scene_shape[1] * halfed_scene_shape))   
    # accu1, accu2 = accuFun(sess, trData, trLabel, bs)     
    # logging.info("A1: %g, A2: %g" % (accu1, accu2))
    # print       ("A1: %g, A2: %g" % (accu1, accu2))
    
    logging.info("Creating ply files...")
    print       ("Creating ply files...")
    
    bs = 0  
    trData, trLabel = [], [] 
    batch_arr = []
    # test_data = utils.fetch_random_batch(test_directory, batch_size)
    
    # for test in test_data:   
        # loaded_file = np.load(test)
        # batch_arr.append(utils.npy_cutter(loaded_file, scene_shape))
        # bs += 1   
        
    # batch_arr = np.reshape( batch_arr, ( bs, scene_shape[0], scene_shape[1], scene_shape[2] ))
    # trData  = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], 0:halfed_scene_shape ]               # input 
    # trLabel = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], halfed_scene_shape:scene_shape[2] ]  # gt     
    # trData  = np.reshape(trData, (-1, scene_shape[0] * scene_shape[1] * halfed_scene_shape))   
    # accu1, accu2 = accuFun(sess, trData, trLabel, bs)     
    # logging.info("A1: %g, A2: %g" % (accu1, accu2))
    # print       ("A1: %g, A2: %g" % (accu1, accu2))
    
    for item in glob.glob(directory + "/*.ply"):
        os.remove(item)
    
    batch_arr = [] 
    name_arr = []    
    counter = 0
    for item in glob.glob(test_directory + '*.npy'):
        name_arr.append(str(item[12:]))
        loaded_file = np.load(item)
        batch_arr.append(utils.npy_cutter(loaded_file, scene_shape))
        counter += 1
        
        # if counter == batch_size:  
    batch_arr = np.reshape( batch_arr, ( -1, scene_shape[0], scene_shape[1], scene_shape[2] ))
    trData  = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], 0:halfed_scene_shape ]               # input 
    trLabel = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], halfed_scene_shape:scene_shape[2] ]  # gt     
    trData  = np.reshape(trData, (-1, scene_shape[0] * scene_shape[1] * halfed_scene_shape))   
    
    score  = sess.run(ConvNet_class.score, feed_dict={x: trData, keepProb: 1.0, phase: False})  
    score  = np.reshape(score, (counter, scene_shape[0], scene_shape[1], halfed_scene_shape, classes_count))
    score  = np.argmax(score, 4) 
    trData = np.reshape(trData, (-1, scene_shape[0], scene_shape[1], halfed_scene_shape))
    
    for i in range(counter):  
        # loaded_file = np.load(test_data[i])
        # scene = utils.npy_cutter(loaded_file, scene_shape)
        
        trData_i = trData[i,:,:,:]
        trData_i  = np.reshape( trData_i, (scene_shape[0], scene_shape[1], halfed_scene_shape))
        
        score_i = score[i,:,:,:]
        score_i = np.reshape( score_i, (scene_shape[0], scene_shape[1], halfed_scene_shape)) 
        
        empty_scene = np.zeros((84,44,42))
        empty_space = np.zeros((scene_shape[0], scene_shape[1], 50)) 
        empty_scene = np.concatenate((trData_i, empty_scene), axis=2)   
        empty_scene = np.concatenate((empty_scene, empty_space), axis=2)  
        gen_scn = np.concatenate((trData_i, score_i), axis=2)  
        gen_scn = np.concatenate((empty_scene, gen_scn), axis=2)   
        empty_space = np.zeros((scene_shape[0], scene_shape[1], 50))
        gen_scn = np.concatenate((gen_scn, empty_space), axis=2) 
        gen_scn = np.concatenate((gen_scn, batch_arr[i,:,:,:]), axis=2) 
        
        output = open( directory + "/" + name_arr[i]  + ".ply" , 'w') 
        ply       = ""
        numOfVrtc = 0
        for idx1 in range(gen_scn.shape[0]):
            for idx2 in range(gen_scn.shape[1]): 
                for idx3 in range(gen_scn.shape[2]):  
                    if gen_scn[idx1][idx2][idx3] > 0:  
                        ply = ply + str(idx1)+ " " +str(idx2)+ " " +str(idx3) + str(utils.colors[ int(gen_scn[idx1][idx2][idx3]) ]) + "\n" 
                        numOfVrtc += 1
                        
        output.write("ply"                                   + "\n")
        output.write("format ascii 1.0"                      + "\n")
        output.write("comment VCGLIB generated"              + "\n")
        output.write("element vertex " +  str(numOfVrtc)     + "\n")
        output.write("property float x"                      + "\n")
        output.write("property float y"                      + "\n")
        output.write("property float z"                      + "\n")
        output.write("property uchar red"                    + "\n")
        output.write("property uchar green"                  + "\n")
        output.write("property uchar blue"                   + "\n")
        output.write("property uchar alpha"                  + "\n")
        output.write("element face 0"                        + "\n")
        output.write("property list uchar int vertex_indices"+ "\n")
        output.write("end_header"                            + "\n")
        output.write( ply                                          ) 
        output.close()
        logging.info(test_data[i][12:] + ".ply" + " is Done!")
        print       (test_data[i][12:] + ".ply" + " is Done!") 
    
    batch_arr = []  
    name_arr = []
    counter = 0

# def show_result(sess): 
    # logging.info("Creating ply files...")
    # print       ("Creating ply files...")
    
    # bs = 0  
    # trData, trLabel   = [], [] 
    # batch_arr         = [] 
    # precision = np.zeros(classes_count)
    # recall = np.zeros(classes_count)
    # accu1_all, accu2_all = 0.0, 0.0
    
    # for counter in range(num_of_vis_batch):
        # trData, trLabel   = [], [] 
        # batch_arr         = []
        # batch_arr_2d      = []
        # bs = 0 
        
        # test_data = utils.fetch_random_batch(train_directory, batch_size)
        
        # for test in test_data:    
            # loaded_file = np.load(test)
            # batch_arr.append(utils.npy_cutter(loaded_file, scene_shape))
            # bs += 1   
            
        # batch_arr    = np.reshape( batch_arr,    ( bs, scene_shape[0], scene_shape[1], scene_shape[2] ))
        # trData    = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], 0:halfed_scene_shape ]               # input 
        # trLabel   = batch_arr[ :, 0:scene_shape[0], 0:scene_shape[1], halfed_scene_shape:scene_shape[2] ]  # gt   
        # trData    = np.reshape(trData,    (-1, scene_shape[0] * scene_shape[1] * halfed_scene_shape))   

        # score       = sess.run( ConvNet_class.score , feed_dict={x: trData, keepProb: 1.0, phase: False})  
        # score       = np.reshape( score, ( -1, scene_shape[0], scene_shape[1], halfed_scene_shape, classes_count ))  
        # score       = np.argmax ( score, 4)     
        # score       = np.reshape( score, ( -1, scene_shape[0], scene_shape[1], halfed_scene_shape )) 
        # pre, rec    = utils.precision_recall(score, trLabel, batch_size, classes_count)
        # precision += pre
        # recall += rec
        
        # accu1, accu2 = accuFun(sess, trData, trLabel, bs)     
        # accu1_all += accu1
        # accu2_all += accu2  
        # logging.info("A1: %g, A2: %g" % (accu1, accu2))
        # print       ("A1: %g, A2: %g" % (accu1, accu2))
       
    # print precision / num_of_vis_batch * 1.0
    # print recall / num_of_vis_batch * 1.0
    # print accu1_all / num_of_vis_batch * 1.0
    # print accu2_all / num_of_vis_batch * 1.0
    
    # for item in glob.glob(directory + "/*.ply"):
        # os.remove(item)    
    
#===================================================================================================================================================

def fetch_x_y(data, limit):
    batch, x, y = [], [], []  
    random_batch = []
    for i in xrange(batch_size): # randomly fetch batch
        random_batch.append(data[random.randint(0, limit-1)])

    for npyFile in random_batch: 
        loaded_scene = np.load(npyFile)
        scene = utils.npy_cutter(loaded_scene, scene_shape) 
        batch.append(scene)
        
    batch = np.reshape( batch, ( -1, scene_shape[0], scene_shape[1], scene_shape[2] ))    

    x = batch[ : , 0:scene_shape[0] , 0:scene_shape[1], 0:halfed_scene_shape ]               # input 
    y = batch[ : , 0:scene_shape[0] , 0:scene_shape[1], halfed_scene_shape:scene_shape[2] ]  # gt  

    x = np.reshape( x, ( -1, scene_shape[0] * scene_shape[1] * halfed_scene_shape ))
    y = np.reshape( y, ( -1, scene_shape[0] * scene_shape[1] * halfed_scene_shape ))

    return x, y

#===================================================================================================================================================
  
if __name__ == '__main__':

    input         = scene_shape[0] * scene_shape[1] * halfed_scene_shape
    out           = scene_shape[0] * scene_shape[1] * halfed_scene_shape  
    x             = tf.placeholder(tf.float32, [ None, input ])
    y             = tf.placeholder(tf.int32  , [ None, out   ])   
    lr            = tf.placeholder(tf.float32                 )   
    keepProb      = tf.placeholder(tf.float32                 )
    phase         = tf.placeholder(tf.bool                    )
    dropOut       = 0.5
    ConvNet_class = ConvNet(x, y, lr, keepProb, phase)
    init_var      = tf.global_variables_initializer() 
    saver         = tf.train.Saver() 
    
    count_params()
    
    # log_device_placement: shows the log of which task will work on which device.
    # allow_soft_placement: TF choose automatically the available device
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)) as sess:  
        sess.run(init_var) 
        
        # restore model weights
        if to_restore:
            if os.path.exists(directory + '/my-model.meta'): 
                new_saver = tf.train.import_meta_graph(directory + '/my-model.meta')
                new_saver.restore(sess, tf.train.latest_checkpoint(directory)) 
                logging.info("\r\n------------ Saved weights restored. ------------")
                print       ("\r\n------------ Saved weights restored. ------------")
                
        # prevent to add extra node to graph during training        
        tf.get_default_graph().finalize()        
        
        # get the updateable operation from graph for batch norm layer
        extra_update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)     
        
        # -------------- test phase --------------
        if to_train == False:  
            show_result(sess) 
            logging.info(".ply files are created.!")
            print (".ply files are created.!")
            sys.exit(0)
        
        # -------------- train phase --------------
        step         = 0
        train_cost   = []
        valid_cost   = []
        train_accu1  = []
        train_accu2  = []
        valid_accu1  = []
        valid_accu2  = [] 
        accu1tr, accu2tr = 0, 0
        
        while(step < max_iter):    
        
            x_batch, y_batch = fetch_x_y(train_data, batch_threshold)  
            
            with tf.control_dependencies(extra_update_ops):  
                cost, _ = sess.run([ConvNet_class.cost, ConvNet_class.update], feed_dict={x: x_batch, y: y_batch, lr: learning_rate, keepProb: dropOut, phase: True})    
                train_cost.append(cost) 
            
            # -------------- prints --------------
            if step%1 == 0: 
                logging.info("%s , S:%3g , lr:%g , accu1: %4.3g , accu2: %4.3g , Cost: %2.3g "% ( str(datetime.datetime.now().time())[:-7], step, learning_rate, accu1tr, accu2tr, cost ))
                print       ("%s , S:%3g , lr:%g , accu1: %4.3g , accu2: %4.3g , Cost: %2.3g "% ( str(datetime.datetime.now().time())[:-7], step, learning_rate, accu1tr, accu2tr, cost ))
            
            # -------------- accuracy calculator --------------  
            if step % show_accuracy_step == 0 and show_accuracy:   
                accu1tr, accu2tr = accuFun(sess, x_batch, y_batch, batch_size)  
                train_accu1.append(accu1tr)
                train_accu2.append(accu2tr) 
                
                # valid accuray
                v_x_batch, v_y_batch = fetch_x_y(test_data, len(test_data)) 
                accu1v, accu2v = accuFun(sess, v_x_batch, v_y_batch, batch_size)  
                valid_accu1.append(accu1v)
                valid_accu2.append(accu2v)
                logging.info("accu1v: %4.3g , accu2v: %4.3g "% ( accu1v, accu2v ))
                print       ("accu1v: %4.3g , accu2v: %4.3g "% ( accu1v, accu2v ))
                
            # -------------- save mode, write cost and accuracy --------------  
            if step % save_model_step == 0 and save_model: 
                logging.info("Saving the model...") 
                print       ("Saving the model...") 
                saver.save(sess, directory + '/my-model')
                logging.info("creating cost and accuray plot files...") 
                print       ("creating cost and accuray plot files...")
                utils.write_cost_accuray_plot(directory, train_cost, valid_cost, train_accu1, train_accu2, valid_accu1, valid_accu2) 
                
            # -------------- visualize scenes -------------- 
            if step % visualize_scene_step == 0 and visualize_scene:
                show_result(sess)
                
            # --------------------------------------------- 
            step += 1    
            
        logging.info(" --- \r\n --- \r\n  Trainig process is done after " + str(max_iter) + " iterations. \r\n --- \r\n ---")
        print       (" --- \r\n --- \r\n  Trainig process is done after " + str(max_iter) + " iterations. \r\n --- \r\n ---")
        
#======================================================================================================================================================== 