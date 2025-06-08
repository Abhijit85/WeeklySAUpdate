import re
import csv

# ------------------------------------------------------------------------------
# 1) Adjust these variables as needed
# ------------------------------------------------------------------------------
INPUT_FILE = "mongo_sizing_input.txt"  # The raw text from your spreadsheet
OUTPUT_FILE = "per_client_cost_dwt.csv"

# Total monthly cost for the entire cluster (example: $240k)
TOTAL_CLUSTER_COST = 240000.0

########################################
# We have two weighting modes:
#  (A) Pure data-size approach (i.e., monthly_cost_i = data_share_i * total)
#  (B) Weighted approach: data vs. IOPS
#
# For the weighted approach, we also have an IOPS_THRESHOLD.
# If a client’s total IOPS (avg_read_ops_s + avg_write_ops_s) >= IOPS_THRESHOLD
# we consider them a "heavy iops" client.
#
# Additionally, we maintain a known set of big IOPS clients ("HEAVY_IOPS_CLIENTS").
# If a client is either in that set, OR if their iops >= IOPS_THRESHOLD, we apply 25/75.
# Otherwise, we do 50/50.
########################################

PURE_DATA_ONLY = True  # Set to True if you want to ignore IOPS and cost by data alone

# The fallback weighting for typical clients:
DEFAULT_DATA_WEIGHT = 0.5
DEFAULT_IOPS_WEIGHT = 0.5

# The heavier weighting for big IOPS clients:
HEAVY_DATA_WEIGHT = 0.25
HEAVY_IOPS_WEIGHT = 0.75

# Known heavy IOPS clients by name:
HEAVY_IOPS_CLIENTS = {"adventhealth", "clevelandclin", "psjhealth"}

# Automatic threshold for large IOPS:
IOPS_THRESHOLD = 4000.0  # Example: treat any client >= 2000 ops/s total as "heavy iops"

# ------------------------------------------------------------------------------
# 2) Helper functions
# ------------------------------------------------------------------------------
def parse_data_size(size_str):
    """
    Convert a size string like "1.26 TB", "897.46 GB", "0.21 MB", "#DIV/0!", "0.56 MB" to float (GB).
    Returns 0.0 if invalid or #DIV/0.
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
        return val  # assume GB if no unit found


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
# 3) Read the input text line by line; parse columns
# ------------------------------------------------------------------------------
clients_data = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        raw_line = line.strip()
        if not raw_line:
            continue  # skip blank lines

        # Attempt a tab split first
        cols = raw_line.split("\t")
        # Fallback if <4 columns
        if len(cols) < 4:
            cols = re.split(r"\s{2,}", raw_line)

        # Identify if it's the 4-column line (client, january, feb, growth)
        # or the 5-column line (client, avg read, avg write, pct read, pct write)
        if len(cols) == 4:
            client_name = cols[0].strip().lower()
            size_2025_02_07 = cols[2].strip()  # e.g. "1.26 TB"
            data_gb = parse_data_size(size_2025_02_07)

            clients_data.append({
                "client": client_name,
                "data_gb": data_gb,
                "avg_read_ops_s": 0.0,
                "avg_write_ops_s": 0.0,
            })

        elif len(cols) == 5:
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
                # create new entry if wasn't in the data table
                clients_data.append({
                    "client": client_name,
                    "data_gb": 0.0,
                    "avg_read_ops_s": read_ops,
                    "avg_write_ops_s": write_ops,
                })


# ------------------------------------------------------------------------------
# 4) Summations
# ------------------------------------------------------------------------------
total_data_gb = sum(d["data_gb"] for d in clients_data)
total_iops = sum(d["avg_read_ops_s"] + d["avg_write_ops_s"] for d in clients_data)

# avoid dividing by zero
if total_data_gb == 0:
    total_data_gb = 1e-9
if total_iops == 0:
    total_iops = 1e-9

# ------------------------------------------------------------------------------
# 5) Calculate cost shares and write CSV
# ------------------------------------------------------------------------------

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([
        "Client",
        "Data_GB",
        "Avg_Read_Ops_s",
        "Avg_Write_Ops_s",
        "Total_IOPS",
        "Data_Share",
        "IOPS_Share",
        "Weighted_Share",
        "Monthly_Cost"
    ])

    for d in clients_data:
        client = d["client"]
        data_gb = d["data_gb"]
        read_ops = d["avg_read_ops_s"]
        write_ops = d["avg_write_ops_s"]
        iops = read_ops + write_ops

        # fraction of total data and total iops
        data_share = data_gb / total_data_gb
        iops_share = iops / total_iops

        if PURE_DATA_ONLY:
            # cost is purely by data
            weighted_share = data_share
        else:
            # Condition: If client is known in HEAVY_IOPS_CLIENTS OR iops >= IOPS_THRESHOLD,
            # we treat them as heavy iops => 25/75.
            # Otherwise => 50/50.
            if (client in HEAVY_IOPS_CLIENTS) or (iops >= IOPS_THRESHOLD):
                data_w = HEAVY_DATA_WEIGHT
                iops_w = HEAVY_IOPS_WEIGHT
            else:
                data_w = DEFAULT_DATA_WEIGHT
                iops_w = DEFAULT_IOPS_WEIGHT

            weighted_share = data_share * data_w + iops_share * iops_w

        monthly_cost = weighted_share * TOTAL_CLUSTER_COST

        writer.writerow([
            client,
            round(data_gb, 3),
            round(read_ops, 3),
            round(write_ops, 3),
            round(iops, 3),
            round(data_share, 6),
            round(iops_share, 6),
            round(weighted_share, 6),
            round(monthly_cost, 2)
        ])

print(f"Done! Wrote CSV to {OUTPUT_FILE}.")
