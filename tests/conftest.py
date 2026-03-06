import os

# Must be set before importing app so Dynaconf loads the [testing] environment
os.environ["LANTERNA_ENV"] = "testing"
