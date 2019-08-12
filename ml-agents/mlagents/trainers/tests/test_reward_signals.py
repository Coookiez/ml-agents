import unittest.mock as mock
import pytest
import mlagents.trainers.tests.mock_brain as mb

import numpy as np
import tensorflow as tf
import yaml
import os

from mlagents.trainers.ppo.models import PPOModel
from mlagents.trainers.ppo.trainer import discount_rewards
from mlagents.trainers.ppo.policy import PPOPolicy
from mlagents.trainers.demo_loader import make_demo_buffer
from mlagents.envs import UnityEnvironment
from mlagents.envs.mock_communicator import MockCommunicator


@pytest.fixture
def dummy_config():
    return yaml.safe_load(
        """
        trainer: ppo
        batch_size: 32
        beta: 5.0e-3
        buffer_size: 512
        epsilon: 0.2
        hidden_units: 128
        lambd: 0.95
        learning_rate: 3.0e-4
        max_steps: 5.0e4
        normalize: true
        num_epoch: 5
        num_layers: 2
        time_horizon: 64
        sequence_length: 64
        summary_freq: 1000
        use_recurrent: false
        memory_size: 8
        curiosity_strength: 0.0
        curiosity_enc_size: 1
        reward_signals:
          extrinsic:
            strength: 1.0
            gamma: 0.99
        """
    )


@pytest.fixture
def gail_dummy_config():
    return {
        "gail": {
            "strength": 0.1,
            "gamma": 0.9,
            "encoding_size": 128,
            "demo_path": os.path.dirname(os.path.abspath(__file__)) + "/test.demo",
        }
    }


@pytest.fixture
def curiosity_dummy_config():
    return {"curiosity": {"strength": 0.1, "gamma": 0.9, "encoding_size": 128}}


VECTOR_ACTION_SPACE = [2]
VECTOR_OBS_SPACE = 8
DISCRETE_ACTION_SPACE = [3, 3, 3, 2]
BUFFER_INIT_SAMPLES = 20
NUM_AGENTS = 12


def create_ppo_policy_mock(
    mock_env, dummy_config, reward_signal_config, use_rnn, use_discrete, use_visual
):
    env, mock_brain, _ = mb.setup_mock_env_and_brains(
        mock_env,
        use_discrete,
        use_visual,
        num_agents=NUM_AGENTS,
        vector_action_space=VECTOR_ACTION_SPACE,
        vector_obs_space=VECTOR_OBS_SPACE,
        discrete_action_space=DISCRETE_ACTION_SPACE,
    )

    trainer_parameters = dummy_config
    model_path = env.brain_names[0]
    trainer_parameters["model_path"] = model_path
    trainer_parameters["keep_checkpoints"] = 3
    trainer_parameters["reward_signals"].update(reward_signal_config)
    trainer_parameters["use_recurrent"] = use_rnn
    policy = PPOPolicy(0, mock_brain, trainer_parameters, False, False)
    return env, policy


def reward_signal_eval(env, policy, reward_signal_name):
    brain_infos = env.reset()
    brain_info = brain_infos[env.brain_names[0]]
    next_brain_info = env.step()[env.brain_names[0]]
    # Test evaluate
    rsig_result = policy.reward_signals[reward_signal_name].evaluate(
        brain_info, next_brain_info
    )
    assert rsig_result.scaled_reward.shape == (NUM_AGENTS,)
    assert rsig_result.unscaled_reward.shape == (NUM_AGENTS,)


def reward_signal_update(env, policy, reward_signal_name):
    buffer = mb.simulate_rollout(env, policy, BUFFER_INIT_SAMPLES)
    out = policy.reward_signals[reward_signal_name].update(buffer.update_buffer, 2)
    assert type(out) is dict


@mock.patch("mlagents.envs.UnityEnvironment")
def test_gail_cc(mock_env, dummy_config, gail_dummy_config):
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, gail_dummy_config, False, False, False
    )
    reward_signal_eval(env, policy, "gail")
    reward_signal_update(env, policy, "gail")


@mock.patch("mlagents.envs.UnityEnvironment")
def test_gail_dc_visual(mock_env, dummy_config, gail_dummy_config):
    gail_dummy_config["gail"]["demo_path"] = (
        os.path.dirname(os.path.abspath(__file__)) + "/testdcvis.demo"
    )
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, gail_dummy_config, False, True, True
    )
    reward_signal_eval(env, policy, "gail")
    reward_signal_update(env, policy, "gail")


@mock.patch("mlagents.envs.UnityEnvironment")
def test_gail_rnn(mock_env, dummy_config, gail_dummy_config):
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, gail_dummy_config, True, False, False
    )
    reward_signal_eval(env, policy, "gail")
    reward_signal_update(env, policy, "gail")


@mock.patch("mlagents.envs.UnityEnvironment")
def test_curiosity_cc(mock_env, dummy_config, curiosity_dummy_config):
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, curiosity_dummy_config, False, False, False
    )
    reward_signal_eval(env, policy, "curiosity")
    reward_signal_update(env, policy, "curiosity")


@mock.patch("mlagents.envs.UnityEnvironment")
def test_curiosity_dc(mock_env, dummy_config, curiosity_dummy_config):
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, curiosity_dummy_config, False, True, False
    )
    reward_signal_eval(env, policy, "curiosity")
    reward_signal_update(env, policy, "curiosity")


@mock.patch("mlagents.envs.UnityEnvironment")
def test_curiosity_visual(mock_env, dummy_config, curiosity_dummy_config):
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, curiosity_dummy_config, False, False, True
    )
    reward_signal_eval(env, policy, "curiosity")
    reward_signal_update(env, policy, "curiosity")


@mock.patch("mlagents.envs.UnityEnvironment")
def test_curiosity_rnn(mock_env, dummy_config, curiosity_dummy_config):
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, curiosity_dummy_config, True, False, False
    )
    reward_signal_eval(env, policy, "curiosity")
    reward_signal_update(env, policy, "curiosity")


@mock.patch("mlagents.envs.UnityEnvironment")
def test_extrinsic(mock_env, dummy_config, curiosity_dummy_config):
    env, policy = create_ppo_policy_mock(
        mock_env, dummy_config, curiosity_dummy_config, False, False, False
    )
    reward_signal_eval(env, policy, "extrinsic")
    reward_signal_update(env, policy, "extrinsic")


if __name__ == "__main__":
    pytest.main()
