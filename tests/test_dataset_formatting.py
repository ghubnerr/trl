# Copyright 2020-2025 The HuggingFace Team. All rights reserved.
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

import unittest
from typing import Callable

from datasets import Dataset, load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

from trl.extras.dataset_formatting import get_formatting_func_from_dataset
from trl.models.utils import ChatMlSpecialTokens, clone_chat_template, setup_chat_format


class DatasetFormattingTestCase(unittest.TestCase):
    def setUp(self):
        self.llama_tokenizer = AutoTokenizer.from_pretrained("trl-internal-testing/tiny-MistralForCausalLM-0.1")
        self.chatml_tokenizer = AutoTokenizer.from_pretrained("trl-internal-testing/tiny-Qwen2ForCausalLM-2.5")

    def test_get_formatting_func_from_dataset_with_chatml_messages(self):
        dataset = Dataset.from_dict(
            {
                "messages": [
                    [
                        {"role": "system", "content": "You are helpful"},
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi, how can I help you?"},
                    ]
                ]
            }
        )

        # Llama tokenizer
        formatting_func = get_formatting_func_from_dataset(dataset, self.llama_tokenizer)
        self.assertIsInstance(formatting_func, Callable)
        formatted_text = formatting_func(dataset[0])
        expected = "<s> [INST] You are helpful\n\nHello [/INST] Hi, how can I help you?</s>"
        self.assertEqual(formatted_text, expected)
        formatted_text = formatting_func(dataset[0:1])
        self.assertListEqual(formatted_text, [expected])

        # ChatML tokenizer
        formatting_func = get_formatting_func_from_dataset(dataset, self.chatml_tokenizer)
        formatted_text = formatting_func(dataset[0])
        expected = "<|im_start|>system\nYou are helpful<|im_end|>\n<|im_start|>user\nHello<|im_end|>\n<|im_start|>assistant\nHi, how can I help you?<|im_end|>\n"
        self.assertEqual(formatted_text, expected)
        formatted_text = formatting_func(dataset[0:1])
        self.assertListEqual(formatted_text, [expected])

    def test_get_formatting_func_from_dataset_with_chatml_conversations(self):
        dataset = Dataset.from_dict(
            {
                "conversations": [
                    [
                        {"role": "system", "content": "You are helpful"},
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi, how can I help you?"},
                    ]
                ]
            }
        )
        # Llama tokenizer
        formatting_func = get_formatting_func_from_dataset(dataset, self.llama_tokenizer)
        self.assertIsInstance(formatting_func, Callable)
        formatted_text = formatting_func(dataset[0])
        expected = "<s> [INST] You are helpful\n\nHello [/INST] Hi, how can I help you?</s>"
        self.assertEqual(formatted_text, expected)
        formatted_text = formatting_func(dataset[0:1])
        self.assertListEqual(formatted_text, [expected])

        # ChatML tokenizer
        formatting_func = get_formatting_func_from_dataset(dataset, self.chatml_tokenizer)
        formatted_text = formatting_func(dataset[0])
        expected = "<|im_start|>system\nYou are helpful<|im_end|>\n<|im_start|>user\nHello<|im_end|>\n<|im_start|>assistant\nHi, how can I help you?<|im_end|>\n"
        self.assertEqual(formatted_text, expected)
        formatted_text = formatting_func(dataset[0:1])
        self.assertListEqual(formatted_text, [expected])

    def test_get_formatting_func_from_dataset_with_instruction(self):
        dataset = Dataset.from_list(
            [{"prompt": "What is 2+2?", "completion": "4"}, {"prompt": "What is 3+3?", "completion": "6"}]
        )
        formatting_func = get_formatting_func_from_dataset(dataset, self.llama_tokenizer)
        self.assertIsNotNone(formatting_func)
        self.assertIsInstance(formatting_func, Callable)
        formatted_text = formatting_func(dataset[0])
        self.assertEqual(formatted_text, "<s> [INST] What is 2+2? [/INST] 4</s>")
        formatted_text = formatting_func(dataset[0:1])
        self.assertListEqual(formatted_text, ["<s> [INST] What is 2+2? [/INST] 4</s>"])

    def test_get_formatting_func_from_dataset_from_hub(self):
        ds_1 = load_dataset("philschmid/trl-test-instruction", split="train")
        ds_2 = load_dataset("philschmid/dolly-15k-oai-style", split="train")
        for ds in [ds_1, ds_2]:
            formatting_func = get_formatting_func_from_dataset(ds, self.llama_tokenizer)
            self.assertIsNotNone(formatting_func)
            self.assertIsInstance(formatting_func, Callable)
        ds_3 = load_dataset("philschmid/guanaco-sharegpt-style", split="train")
        formatting_func = get_formatting_func_from_dataset(ds_3, self.llama_tokenizer)
        self.assertIsNone(formatting_func)

    def test_get_formatting_func_from_dataset_with_unknown_format(self):
        dataset = Dataset.from_dict({"text": "test"})
        formatting_func = get_formatting_func_from_dataset(dataset, self.llama_tokenizer)
        self.assertIsNone(formatting_func)


class SetupChatFormatTestCase(unittest.TestCase):
    def setUp(self):
        self.tokenizer = AutoTokenizer.from_pretrained("trl-internal-testing/tiny-Qwen2ForCausalLM-2.5")
        self.model = AutoModelForCausalLM.from_pretrained("trl-internal-testing/tiny-Qwen2ForCausalLM-2.5")
        # remove built-in chat_template to simulate a model having no chat_template
        self.tokenizer.chat_template = None

    def test_setup_chat_format(self):
        modified_model, modified_tokenizer = setup_chat_format(
            self.model, self.tokenizer, format="chatml", resize_to_multiple_of=123
        )

        _chatml = ChatMlSpecialTokens()
        # Check if special tokens are correctly set
        self.assertEqual(modified_tokenizer.eos_token, "<|im_end|>")
        self.assertEqual(modified_tokenizer.pad_token, "<|im_end|>")
        self.assertEqual(modified_tokenizer.bos_token, "<|im_start|>")
        self.assertEqual(modified_tokenizer.eos_token, _chatml.eos_token)
        self.assertEqual(modified_tokenizer.pad_token, _chatml.pad_token)
        self.assertEqual(modified_tokenizer.bos_token, _chatml.bos_token)
        self.assertEqual((modified_model.vocab_size % 123), 0)

    def test_example_with_setup_model(self):
        modified_model, modified_tokenizer = setup_chat_format(
            self.model,
            self.tokenizer,
        )
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi, how can I help you?"},
        ]
        prompt = modified_tokenizer.apply_chat_template(messages, tokenize=False)

        self.assertEqual(
            prompt,
            "<|im_start|>system\nYou are helpful<|im_end|>\n<|im_start|>user\nHello<|im_end|>\n<|im_start|>assistant\nHi, how can I help you?<|im_end|>\n",
        )


class CloneChatTemplateTestCase(unittest.TestCase):
    def setUp(self):
        # This tokenizer doesn't have a chat_template by default
        self.tokenizer = AutoTokenizer.from_pretrained("trl-internal-testing/tiny-BloomForCausalLM")
        self.model = AutoModelForCausalLM.from_pretrained("trl-internal-testing/tiny-BloomForCausalLM")
        # This one has a chat_template by default
        self.source = "trl-internal-testing/tiny-Qwen3ForCausalLM"

    def test_clone(self):
        _, modified_tokenizer, _ = clone_chat_template(self.model, self.tokenizer, self.source)

        # Check if special tokens are correctly set
        self.assertEqual(modified_tokenizer.eos_token, "<|im_end|>")

    def test_clone_with_resize(self):
        modified_model, modified_tokenizer, _ = clone_chat_template(
            self.model, self.tokenizer, self.source, resize_to_multiple_of=123
        )

        # Check that the input embeddings have been resized to a multiple of 123
        self.assertEqual((modified_model.vocab_size % 123), 0)
        # Check that the input embeddings size matches the tokenizer vocabulary size
        self.assertEqual(self.model.vocab_size, len(modified_tokenizer.vocab))

    def test_clone_with_resize_and_extra_tokens_already_in_vocab(self):
        # This will add <extra_id_0>, <extra_id_1>, ... to the tokenizer
        modified_model, modified_tokenizer, _ = clone_chat_template(
            self.model, self.tokenizer, self.source, resize_to_multiple_of=123
        )
        # Try if we can resize a tokenizer that already has extra these extra tokens
        modified_model, modified_tokenizer, _ = clone_chat_template(
            modified_model, modified_tokenizer, self.source, resize_to_multiple_of=124
        )

        # Check that the input embeddings have been resized to a multiple of 123
        self.assertEqual((modified_model.vocab_size % 124), 0)
        # Check that the input embeddings size matches the tokenizer vocabulary size
        self.assertEqual(self.model.vocab_size, len(modified_tokenizer.vocab))

    def test_apply_new_chat_template(self):
        _, modified_tokenizer, _ = clone_chat_template(self.model, self.tokenizer, self.source)
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi, how can I help you?"},
        ]
        prompt = modified_tokenizer.apply_chat_template(messages, tokenize=False)

        self.assertEqual(
            prompt,
            "<|im_start|>system\nYou are helpful<|im_end|>\n<|im_start|>user\nHello<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\nHi, how can I help you?<|im_end|>\n",
        )
