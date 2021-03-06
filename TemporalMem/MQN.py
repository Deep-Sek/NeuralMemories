import os
import sys

import gym
import keras.backend as K
import matplotlib.pyplot as plt
import numpy as np
from keras.optimizers import RMSprop

from ..rl.agents.dqn import DQNAgent
from .MQNModel import MQNmodel
from ..rl.callbacks import TrainEpisodeLogger
from ..rl.memory import SequentialMemory
from ..rl.policy import EpsGreedyQPolicy, LinearAnnealedPolicy


# Need to update environment to have indicator tiles
# Need better metrics (percent of episodes)
# Need model saving / loading
# Need model visualization ability

def visualizeLayer(model, layer, sample):
    inputs = [K.learning_phase()] + model.inputs

    _output = K.function(inputs, [layer.output])

    def output(x):
        return _output([0] + [x])

    output = output(sample)
    output = np.squeeze(output)

    n = int(np.ceil(np.sqrt(output.shape[0])))
    fig = plt.figure(figsize=(12, 8))
    for i in range(output.shape[0]):
        ax = fig.add_subplot(n, n, i + 1)
        im = ax.imshow(output[i], cmap='jet')

    # plt.imshow(output[0], cmap='jet')
    cbar_ax = fig.add_axes([0.15, 0.05, 0.7, 0.02])
    fig.colorbar(im, cax=cbar_ax, orientation='horizontal')
    plt.show()

    # print output
    # print "Output shape: ", output.shape


def showmetrics(log):
    ##### Metrics #####
    episodic_reward_means = []
    episodic_losses = []
    episodic_mean_q = []

    for key, value in log.rewards.items():
        episodic_reward_means.append(np.mean(log.rewards[key]))

    for key, value in log.episodic_metrics_variables.items():
        for i in range(0, len(log.episodic_metrics_variables[key]), 2):
            name = log.episodic_metrics_variables[key][i]
            val = log.episodic_metrics_variables[key][i + 1]
            if (name == "loss" and val != '--'):
                episodic_losses.append(val)
            if (name == "mean_q" and val != '--'):
                episodic_mean_q.append(val)

                # Running average
                # episodic_reward_means = (np.cumsum(episodic_reward_means)
                # / (np.arange(len(episodic_reward_means)) + 1))

    plt.figure(1)
    plt.subplot(311)
    plt.title("Loss per Episode")
    plt.plot(episodic_losses, 'b')

    plt.subplot(312)
    plt.title("Mean Q Value per Episode")
    plt.plot(episodic_mean_q, 'r')

    plt.subplot(313)
    plt.title("Reward")
    plt.plot(episodic_reward_means, 'g')
    plt.show()


def main(weights_file):
    # Initialize maze environments.

    # env = gym.make('MazeF4-v0')
    # env2 = gym.make('MazeF1-v0')
    # env3 = gym.make('MazeF2-v0')
    # env4 = gym.make('MazeF3-v0')
    # env5 = gym.make('Maze5-v0')
    # env6 = gym.make('BMaze4-v0')

    # envs = [env,env2,env3,env4,env5,env6]

    # env = gym.make('BMaze4-v0')
    env = gym.make('IMaze2-v0')

    envs = [env]
    # Setting hyperparameters.
    nb_actions = env.action_space.n
    e_t_size = 256
    context_size = 256
    nb_steps_warmup = int(1e5)
    nb_steps = int(1e6)
    buffer_size = 5e4
    learning_rate = 2e-4
    target_model_update = 0.999
    clipnorm = 20.
    switch_rate = 50

    # Callbacks
    log = TrainEpisodeLogger()
    callbacks = [log]

    # Initialize our model.
    model = MQNmodel(e_t_size, context_size, nb_actions)
    target_model = MQNmodel(e_t_size, context_size, nb_actions)
    target_model.set_weights(model.get_weights())

    # Initialize memory buffer and policy for DQN algorithm.
    experience = [SequentialMemory(limit=int(buffer_size / len(envs)), window_length=1) for i in range(len(envs))]

    policy = LinearAnnealedPolicy(
        inner_policy=EpsGreedyQPolicy(),
        attr="eps",
        value_max=1.0,
        value_min=0.1,
        value_test=0.,
        nb_steps=nb_steps_warmup
    )

    # Initialize and compile the DQN agent.
    dqn = DQNAgent(model=model, target_model=target_model, nb_actions=nb_actions, memory=experience,
                   nb_steps_warmup=nb_steps_warmup, target_model_update=target_model_update, policy=policy,
                   batch_size=32)

    dqn.compile(RMSprop(lr=learning_rate, clipnorm=clipnorm), metrics=["mae"])
    observation = env.reset()
    # print env.maze.matrix.shape
    observation = np.reshape(observation, ((1, 1,) + env.maze.matrix.shape))
    # print observation
    # print dqn.layers[1]
    # Load weights if weight file exists.

    if os.path.exists(weights_file):
        dqn.load_weights(weights_file)

    # Train DQN in environment.
    dqn.fit(env, nb_steps=nb_steps, verbose=0, callbacks=callbacks)
    # dqn.test(env, nb_episodes=10,visualize=True)

    # Save weights if weight file does not exist.

    if not os.path.exists(weights_file):
        dqn.save_weights(weights_file)

    # Visualization Tools
    showmetrics(log)
    visualizeLayer(dqn.model, dqn.layers[1], observation)

    return


if __name__ == "__main__":

    weights_file = None

    if len(sys.argv) == 2:
        if (sys.argv[1].split('.')[-1] == "h5"):
            weights_file = sys.argv[1]
        else:
            print
            "File extension must be .h5"
            sys.exit()
    else:
        print
        "Incorrect number of arguments."
        print
        "Usage: python MQN.py [weight_filename].h5"
        sys.exit()

    main(weights_file)