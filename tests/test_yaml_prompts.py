"""YAML legible, errores de sintaxis/schema y rechazo de tags ejecutables."""

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from src.llm.prompts import load_prompt


class YamlPromptTests(unittest.TestCase):
    def test_multiline_yaml_is_loaded_and_validated(self):
        text = """version: v1_zero_shot
technique: zero_shot
instructions: |-
  Clasificá el ticket.
  Devolvé JSON.
examples: []
"""
        with patch("pathlib.Path.read_text", return_value=text):
            prompt = load_prompt("v1_zero_shot")
        self.assertEqual(prompt.instructions, "Clasificá el ticket.\nDevolvé JSON.")
        self.assertEqual(prompt.render(), prompt.instructions)

    def test_malformed_yaml_is_controlled_value_error(self):
        with (
            patch("pathlib.Path.read_text", return_value="instructions: ["),
            self.assertRaisesRegex(ValueError, "YAML inválido"),
        ):
            load_prompt("v1_zero_shot")

    def test_unsafe_python_tag_is_rejected_without_execution(self):
        text = "!!python/object/apply:os.system ['echo SHOULD_NOT_RUN']"
        with (
            patch("pathlib.Path.read_text", return_value=text),
            patch("os.system") as execute,
        ):
            with self.assertRaisesRegex(ValueError, "tags no admitidos"):
                load_prompt("v1_zero_shot")
        execute.assert_not_called()

    def test_yaml_scalar_coercions_still_have_to_pass_strict_schema(self):
        # PyYAML reconoce yes como booleano. La instrucción tiene que ser texto.
        text = """version: v1_zero_shot
technique: zero_shot
instructions: yes
examples: []
"""
        with (
            patch("pathlib.Path.read_text", return_value=text),
            self.assertRaises(ValidationError),
        ):
            load_prompt("v1_zero_shot")


if __name__ == "__main__":
    unittest.main()
