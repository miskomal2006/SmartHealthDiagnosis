from marshmallow import Schema, fields, validate, ValidationError


# =============================
# REGISTER VALIDATION
# =============================

class RegisterSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=3))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8))
    role = fields.String(required=True, validate=validate.OneOf(["patient","doctor","admin"]))


# =============================
# LOGIN VALIDATION
# =============================

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


# =============================
# DIAGNOSIS VALIDATION
# =============================

class DiagnosisSchema(Schema):
    disease_target = fields.String(
        required=True,
        validate=validate.OneOf(["diabetes", "heart", "respiratory", "kidney", "liver", "cancer"])
    )

    patient = fields.Dict(required=True)
    vitals = fields.Dict(required=True)

    symptoms = fields.List(fields.String(), required=True)

    metadata = fields.Dict(required=True)

    medicalHistory = fields.String(required=False)
    smoking = fields.String(required=False)
    alcohol = fields.String(required=False)
    activity = fields.String(required=False)
    sleep = fields.Float(required=False)
    stress = fields.Integer(required=False)
