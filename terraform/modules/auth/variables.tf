variable "name" {
  description = "Name prefix for the user pool and client (e.g. catan-prod)."
  type        = string
}

variable "password_minimum_length" {
  description = "Minimum password length enforced by the pool."
  type        = number
  default     = 8
}

variable "generate_client_secret" {
  description = "Create a confidential app client. The backend supports both; false keeps COGNITO_CLIENT_SECRET out of the picture."
  type        = bool
  default     = false
}

variable "access_token_validity_minutes" {
  description = "Lifetime of access and ID tokens in minutes."
  type        = number
  default     = 60
}

variable "refresh_token_validity_days" {
  description = "Lifetime of refresh tokens in days."
  type        = number
  default     = 30
}

variable "deletion_protection" {
  description = "Block terraform destroy from deleting the user pool (and every user in it)."
  type        = bool
  default     = true
}
