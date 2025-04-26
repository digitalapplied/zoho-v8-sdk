import os, traceback
from dotenv import load_dotenv
from zohocrmsdk.src.com.zoho.crm.api.record import RecordOperations, BodyWrapper, Record, APIException, SuccessResponse, ActionWrapper, GetRecordParam
from zohocrmsdk.src.com.zoho.crm.api import ParameterMap, HeaderMap

from initialize_zcrmv8 import Initializer  # just to ensure init has run

_REQ_FIELDS = ["Last_Name", "Company", "Lead_Status"]
MODULE = "Leads"

load_dotenv()
lead_id = int(os.environ["LEAD_ID"])
new_mobile = os.environ["NEW_MOBILE"]

ops = RecordOperations(MODULE)

# ---- 1 · fetch mandatory bits ----
params = ParameterMap()
params.add(GetRecordParam.fields, ",".join(_REQ_FIELDS))
resp = ops.get_record(lead_id, params, HeaderMap())
rec = resp.get_object().get_data()[0]

# ---- 2 · build update payload ----
patch = Record()
for f in _REQ_FIELDS:
    patch.add_key_value(f, rec.get_key_value(f))
patch.add_key_value("Mobile", new_mobile)

body = BodyWrapper(); body.set_data([patch]); body.set_trigger(["workflow", "blueprint"])

# ---- 3 · push ----
try:
    result = ops.update_record(lead_id, body).get_object().get_data()[0]
    if isinstance(result, SuccessResponse):
        print("✔ Lead updated →", result.get_details())
    else:
        print("✖ Update failed →", result.get_message().get_value())
except APIException as ex:
    print("✖ APIException:", ex.get_message().get_value())
    traceback.print_exc()
