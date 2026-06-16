# -------------- # Replace triggers -------------- #

resource "terraform_data" "replace_triggers" {
  triggers_replace = var.replace_triggers
}
