# -------------- # Replace triggers -------------- #

resource "terraform_data" "app_replace_trigger" {
  triggers_replace = var.replace_triggers
}
