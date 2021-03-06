# coding=utf-8
# Copyright 2018 The TF-Agents Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python2, python3
"""Utility functions for configuring environments with Gin."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
import gin
import numpy as np
from six.moves import range
import tensorflow as tf  # pylint: disable=g-explicit-tensorflow-version-import

from tf_agents.bandits.environments import wheel_py_environment


@gin.configurable
class LinearNormalReward(object):
  """A class that acts as linear reward function when called."""

  def __init__(self, theta, sigma):
    self.theta = theta
    self.sigma = sigma

  def __call__(self, x, enable_noise=True):
    """Outputs reward given observation.

    Args:
      x: Observation vector.
      enable_noise: Whether to add normal noise to the reward or not.

    Returns:
      A scalar value: the reward.
    """
    mu = np.dot(x, self.theta)
    if enable_noise:
      return np.random.normal(mu, self.sigma)
    return mu


@gin.configurable
def linear_reward_fn_generator(theta_list, variance):
  return [LinearNormalReward(theta, variance) for theta in theta_list]


@gin.configurable
def sliding_linear_reward_fn_generator(context_dim, num_actions, variance):
  """A function that returns `num_actions` noisy linear functions.

  Every linear function has an underlying parameter consisting of `context_dim`
  consecutive integers. For example, with `context_dim = 3` and
  `num_actions = 2`, the parameter of the linear function associated with
  action 1 is `[1.0, 2.0, 3.0]`.

  Args:
    context_dim: Number of parameters per function.
    num_actions: Number of functions returned.
    variance: Variance of the noisy linear functions.

  Returns:
    A list of noisy linear functions.
  """

  def _float_range(begin, end):
    return [float(j) for j in range(begin, end)]

  return linear_reward_fn_generator(
      [_float_range(i, i + context_dim) for i in range(num_actions)], variance)


@gin.configurable
def context_sampling_fn(batch_size, context_dim):
  return np.random.randint(
      -10, 10, [batch_size, context_dim]).astype(np.float32)


@gin.configurable
def compute_optimal_reward(observation, per_action_reward_fns,
                           enable_noise=False):
  """Computes the optimal reward.

  Args:
    observation: a (possibly batched) observation.
    per_action_reward_fns: a list of reward functions; one per action. Each
      reward function generates a reward when called with an observation.
    enable_noise: (bool) whether to add noise to the rewards.

  Returns:
    The optimal reward.
  """
  num_actions = len(per_action_reward_fns)
  rewards = np.stack(
      [per_action_reward_fns[a](observation, enable_noise)
       for a in range(num_actions)],
      axis=-1)
  # `rewards` should be of shape [`batch_size`, `num_actions`].
  optimal_action_reward = np.max(rewards, axis=-1)
  return optimal_action_reward


@gin.configurable
def tf_compute_optimal_reward(observation,
                              per_action_reward_fns,
                              enable_noise=False):
  """TF wrapper around `compute_optimal_reward` to be used in `tf_metrics`."""
  compute_optimal_reward_fn = functools.partial(
      compute_optimal_reward,
      per_action_reward_fns=per_action_reward_fns,
      enable_noise=enable_noise)
  return tf.py_function(compute_optimal_reward_fn, [observation], tf.float32)


@gin.configurable
def compute_optimal_action(observation,
                           per_action_reward_fns,
                           enable_noise=False):
  """Computes the optimal action.

  Args:
    observation: a (possibly batched) observation.
    per_action_reward_fns: a list of reward functions; one per action. Each
      reward function generates a reward when called with an observation.
    enable_noise: (bool) whether to add noise to the rewards.

  Returns:
    The optimal action, that is, the one with the highest reward.
  """
  num_actions = len(per_action_reward_fns)
  rewards = np.stack([
      per_action_reward_fns[a](observation, enable_noise)
      for a in range(num_actions)
  ],
                     axis=-1)

  optimal_action = np.argmax(rewards, axis=-1)
  return optimal_action


@gin.configurable
def tf_compute_optimal_action(observation,
                              per_action_reward_fns,
                              enable_noise=False,
                              action_dtype=tf.int32):
  """TF wrapper around `compute_optimal_action` to be used in `tf_metrics`."""
  compute_optimal_action_fn = functools.partial(
      compute_optimal_action,
      per_action_reward_fns=per_action_reward_fns,
      enable_noise=enable_noise)
  return tf.py_function(compute_optimal_action_fn, [observation], action_dtype)


@gin.configurable
def compute_optimal_reward_with_environment_dynamics(
    observation, environment_dynamics):
  """Computes the optimal reward using the environment dynamics.

  Args:
    observation: a (possibly batched) observation.
    environment_dynamics: environment dynamics object (an instance of
      `non_stationary_stochastic_environment.EnvironmentDynamics`)

  Returns:
    The optimal reward.
  """
  return environment_dynamics.compute_optimal_reward(observation)


@gin.configurable
def compute_optimal_action_with_environment_dynamics(
    observation, environment_dynamics):
  """Computes the optimal action using the environment dynamics.

  Args:
    observation: a (possibly batched) observation.
    environment_dynamics: environment dynamics object (an instance of
      `non_stationary_stochastic_environment.EnvironmentDynamics`)

  Returns:
    The optimal action.
  """
  return environment_dynamics.compute_optimal_action(observation)


@gin.configurable
def compute_optimal_action_with_classification_environment(
    observation, environment):
  """Helper function for gin configurable SuboptimalArms metric."""
  del observation
  return environment.compute_optimal_action()


@gin.configurable
def compute_optimal_reward_with_classification_environment(
    observation, environment):
  """Helper function for gin configurable Regret metric."""
  del observation
  return environment.compute_optimal_reward()


@gin.configurable
def tf_wheel_bandit_compute_optimal_action(observation,
                                           delta,
                                           action_dtype=tf.int32):
  """TF wrapper around `compute_optimal_action` to be used in `tf_metrics`."""
  return tf.py_function(wheel_py_environment.compute_optimal_action,
                        [observation, delta], action_dtype)


@gin.configurable
def tf_wheel_bandit_compute_optimal_reward(observation, delta, mu_inside,
                                           mu_high):
  """TF wrapper around `compute_optimal_reward` to be used in `tf_metrics`."""
  return tf.py_function(wheel_py_environment.compute_optimal_reward,
                        [observation, delta, mu_inside, mu_high], tf.float32)
