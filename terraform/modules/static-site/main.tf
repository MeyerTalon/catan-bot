# Private S3 bucket fronted by CloudFront via Origin Access Control, serving a
# Vite/React single-page app (403/404 rewrite to index.html). Optionally the
# same distribution proxies /api/* to an HTTP origin (the backend ALB), which
# gives the API free TLS and the same origin as the frontend — no CORS, no
# mixed-content, no certificate or domain needed.

locals {
  s3_origin_id  = "s3-${var.name}"
  api_origin_id = "api-${var.name}"
  api_enabled   = var.enable_api_origin
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "caching_disabled" {
  count = local.api_enabled ? 1 : 0

  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  count = local.api_enabled ? 1 : 0

  name = "Managed-AllViewerExceptHostHeader"
}

# the managed SecurityHeadersPolicy has no content-security-policy, which is
# the one header that limits what an xss can do with the tokens the spa keeps
resource "aws_cloudfront_response_headers_policy" "this" {
  name = "${var.name}-security-headers"

  security_headers_config {
    content_security_policy {
      content_security_policy = var.content_security_policy
      override                = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }
}

# ---------------------------------------------------------------------------
# bucket
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "this" {
  bucket        = var.bucket_name
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

data "aws_iam_policy_document" "bucket" {
  statement {
    sid       = "AllowCloudFrontRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.bucket.json

  depends_on = [aws_s3_bucket_public_access_block.this]
}

# ---------------------------------------------------------------------------
# distribution
# ---------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "this" {
  name                              = "${var.name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# spa fallback: paths without a file extension are client-side routes and get
# index.html. done here rather than with custom_error_response so api 403/404s
# reach the browser as-is instead of as a 200 with html
resource "aws_cloudfront_function" "spa_fallback" {
  name    = "${var.name}-spa-fallback"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-JS
    function handler(event) {
      var request = event.request;
      var last = request.uri.substring(request.uri.lastIndexOf("/") + 1);
      if (last.indexOf(".") === -1) {
        request.uri = "/index.html";
      }
      return request;
    }
  JS
}

# strips the api prefix so the backend sees its own routes (free: 2M invocations/month)
resource "aws_cloudfront_function" "strip_api_prefix" {
  count = local.api_enabled ? 1 : 0

  name    = "${var.name}-strip-api-prefix"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-JS
    function handler(event) {
      var request = event.request;
      var prefix = "${var.api_path_prefix}";
      if (request.uri.indexOf(prefix) === 0) {
        request.uri = request.uri.substring(prefix.length) || "/";
      }
      return request;
    }
  JS
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = "http2and3"
  default_root_object = "index.html"
  comment             = var.name
  price_class         = "PriceClass_100" # north america + europe edges only

  origin {
    domain_name              = aws_s3_bucket.this.bucket_regional_domain_name
    origin_id                = local.s3_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
  }

  dynamic "origin" {
    for_each = local.api_enabled ? [1] : []
    content {
      domain_name = var.api_origin_domain_name
      origin_id   = local.api_origin_id

      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "http-only" # the alb has no certificate; traffic stays inside aws
        origin_ssl_protocols   = ["TLSv1.2"]
      }

      # proves to the origin that the request came through this distribution
      dynamic "custom_header" {
        for_each = var.api_origin_custom_headers
        content {
          name  = custom_header.key
          value = custom_header.value
        }
      }
    }
  }

  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    target_origin_id           = local.s3_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.this.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_fallback.arn
    }
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.api_enabled ? [1] : []
    content {
      path_pattern             = "${var.api_path_prefix}/*"
      allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods           = ["GET", "HEAD"]
      target_origin_id         = local.api_origin_id
      viewer_protocol_policy   = "redirect-to-https"
      compress                 = true
      cache_policy_id          = data.aws_cloudfront_cache_policy.caching_disabled[0].id
      origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host[0].id

      function_association {
        event_type   = "viewer-request"
        function_arn = aws_cloudfront_function.strip_api_prefix[0].arn
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
