import re
import csv

# ------------------------------------------------------------------------------
# 1) Adjust these variables as needed
# ------------------------------------------------------------------------------
INPUT_FILE = "mongo_sizing_input.txt"   # The raw text from your spreadsheet
OUTPUT_FILE = "per_client_estimate_cluster_segregation.csv" # Output CSV: each client is its own cluster

# Thresholds for classification
DATA_INTENSIVE_THRESHOLD = 1024.0   # GB (example: >= 1 TB is "data-intensive")
IOPS_INTENSIVE_THRESHOLD = 4000.0   # ops/s (example: >= 4000 ops/s is "iops-intensive")

# Example cluster tiers & monthly costs (rough placeholder values)
# In reality, you would choose more precise tiers/costs, e.g. from official MongoDB Atlas pricing.
# Adjust these to fit your environment. For demonstration:
CLUSTER_TIERS = {
    "M30": 1500.0,  # up to ~200 GB / moderate ops
    "M50": 3000.0,  # up to ~1-2 TB / moderate ops
    "M100": 5000.0, # up to ~2-5 TB / higher ops
    "M200": 8000.0, # up to ~10 TB or heavy ops
}

def recommend_cluster_tier(data_gb, iops):
    """
    Simple logic:
    1) If both data and IOPS are large, pick bigger tier (M200).
    2) If only data is large, pick M100 or M200 depending on how large data is.
    3) If only IOPS is large, pick M100 or M200.
    4) Otherwise pick a smaller tier (M30, M50).
    Adjust as needed for real usage.
    """
    # We'll do a simple check. You can refine logic further.
    if data_gb >= 5000 or iops >= 15000:
        # Very large data or extremely high ops
        return "M200"
    elif data_gb >= 2000 or iops >= 8000:
        return "M100"
    elif data_gb >= 500 or iops >= 2000:
        return "M50"
    else:
        return "M30"

# ------------------------------------------------------------------------------
# 2) Helper functions to parse input
# ------------------------------------------------------------------------------
def parse_data_size(size_str):
    """
    Convert a size string like "1.26 TB", "897.46 GB", "0.21 MB", "#DIV/0!",
    "0.56 MB" to float (GB). Returns 0.0 if invalid or #DIV/0.
    """
    size_str = size_str.strip().lower()
    if "#div/0" in size_str or size_str == "0.00 mb" or size_str.startswith("0.00"):
        return 0.0
    if size_str == "0.00 mb" or size_str == "":
        return 0.0

    match = re.match(r"([\d\.]+)", size_str)
    if not match:
        return 0.0
    val = float(match.group(1))

    if "tb" in size_str:
        return val * 1024.0  # TB -> GB
    elif "gb" in size_str:
        return val
    elif "mb" in size_str:
        return val / 1024.0  # MB -> GB
    else:
        # default assume GB
        return val

def parse_float_maybe(s):
    """
    Try to parse a float from a string that might have various quirks (#DIV/0, empty).
    Return 0.0 if not valid.
    """
    s = s.strip().lower()
    if "#div/0" in s or not s:
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

# ------------------------------------------------------------------------------
# 3) Read input data
# ------------------------------------------------------------------------------
clients_data = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        raw_line = line.strip()
        if not raw_line:
            continue  # skip blank lines

        # Attempt a tab split first
        cols = raw_line.split("\t")
        # fallback: split on multiple spaces if <4 columns
        if len(cols) < 4:
            cols = re.split(r"\s{2,}", raw_line)

        if len(cols) == 4:
            # e.g. "aahs  1.24 TB  1.26 TB  1.75%"
            client_name = cols[0].strip().lower()
            size_2025_02_07 = cols[2].strip()
            data_gb = parse_data_size(size_2025_02_07)

            clients_data.append({
                "client": client_name,
                "data_gb": data_gb,
                "avg_read_ops_s": 0.0,
                "avg_write_ops_s": 0.0
            })

        elif len(cols) == 5:
            # e.g. "aahs  884.711 421.300 67.74% 32.26%"
            client_name = cols[0].strip().lower()
            read_ops = parse_float_maybe(cols[1])
            write_ops = parse_float_maybe(cols[2])

            found = False
            for d in clients_data:
                if d["client"] == client_name:
                    d["avg_read_ops_s"] = read_ops
                    d["avg_write_ops_s"] = write_ops
                    found = True
                    break

            if not found:
                # create new entry if not found in data lines
                clients_data.append({
                    "client": client_name,
                    "data_gb": 0.0,
                    "avg_read_ops_s": read_ops,
                    "avg_write_ops_s": write_ops
                })

# ------------------------------------------------------------------------------
# 4) Classify each client & recommend a cluster
# ------------------------------------------------------------------------------
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "Client",
        "Data_GB",
        "Avg_Read_Ops_s",
        "Avg_Write_Ops_s",
        "Total_IOPS",
        "Classification",
        "Recommended_Cluster",
        "Estimated_Monthly_Cost"
    ])

    for d in clients_data:
        client = d["client"]
        data_gb = d["data_gb"]
        read_ops = d["avg_read_ops_s"]
        write_ops = d["avg_write_ops_s"]
        iops = read_ops + write_ops

        # Classify
        data_intensive = (data_gb >= DATA_INTENSIVE_THRESHOLD)
        iops_intensive = (iops >= IOPS_INTENSIVE_THRESHOLD)

        if data_intensive and iops_intensive:
            classification = "Data+IOPS Intensive"
        elif data_intensive:
            classification = "Data-Intensive"
        elif iops_intensive:
            classification = "IOPS-Intensive"
        else:
            classification = "Moderate"

        # Recommend cluster tier
        tier = recommend_cluster_tier(data_gb, iops)
        monthly_cost = CLUSTER_TIERS.get(tier, 2000.0)  # fallback cost if not found

        writer.writerow([
            client,
            round(data_gb, 3),
            round(read_ops, 3),
            round(write_ops, 3),
            round(iops, 3),
            classification,
            tier,
            round(monthly_cost, 2)
        ])

print(f"Done! Wrote CSV to {OUTPUT_FILE}.")
