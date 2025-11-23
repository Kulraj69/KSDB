from ksdb.client import Collection
import inspect

print("Inspecting Collection.add signature:")
sig = inspect.signature(Collection.add)
print(sig)

if "deduplicate" in sig.parameters:
    print("✅ 'deduplicate' parameter found.")
else:
    print("❌ 'deduplicate' parameter NOT found.")
