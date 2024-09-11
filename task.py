import os
import sys
import csv
import json
import numpy as np
import tkinter as tk
import multiprocessing
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta

today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

master_file = ".task_master"
stable_daily_log = ""
config_file = ""
data_file = ""
args = {}
master_data = {}
config = {}
ARGS = ["--file", "--create", "--set-default", "--list", "--delete", "-r", "-s" , "--default"]

def read_file_as_dict(file_path):
    data_dict = {}
    try:
        with open(file_path, 'r') as json_file:
            data_dict = json.load(json_file)
    except Exception as e:
        print(f"An error occurred: {e}")
    return data_dict

def read_data_from_file(file_path):
    data = []
    with open(file_path, "r") as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 2:
                date_str, number_str = row
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    number = float(number_str)
                    data.append((date, number))
                except ValueError:
                    continue
    return data

def progress_bar(percentage, bar_length=50):
    if percentage < 0:
        percentage = 0
    elif percentage > 100:
        percentage = 100

    filled_length = int(bar_length * percentage // 100)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    s = f"|{bar}| {percentage:.2f}%"
    print(s)

def create_month_heat_map(values):
    dates_values = {date: value for date, value in values}
    all_dates = sorted(dates_values.keys())
    if not all_dates:
        raise ValueError("The input list is empty.")
    start_date = all_dates[0].replace(day=1)
    end_date = (all_dates[-1] + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    current_date = start_date
    date_to_value = {}

    while current_date <= end_date:
        date_to_value[current_date] = dates_values.get(current_date, np.nan)
        current_date += timedelta(days=1)
    ordered_dates = sorted(date_to_value.keys())
    ordered_values = [date_to_value[date] for date in ordered_dates]

    num_days = len(ordered_dates)
    num_weeks = (num_days + 6) // 7
    heatmap_data = np.full((num_weeks, 7), np.nan)

    for i, date in enumerate(ordered_dates):
        week = ((date - start_date).days // 7)    
        day_of_week = date.weekday()
        heatmap_data[week, day_of_week] = date_to_value[date]

    colors = [(0.9, 1, 0.9), (0, 0.4, 0)]
    n_bins = 100
    cmap_name = "green_scale"
    cm = mcolors.LinearSegmentedColormap.from_list(cmap_name, colors, N=n_bins)
    cm.set_bad(color="#2b2b2b")

    fig, ax = plt.subplots(figsize=(10, 6))
    cax = ax.matshow(heatmap_data, cmap=cm, interpolation="nearest", vmin=0, vmax=10)

    ax.set_xticks(np.arange(7))
    ax.set_xticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], color="white")

    ax.set_yticks(np.arange(num_weeks))
    ax.set_yticklabels([f"Week {i+1}" for i in range(num_weeks)], color="white")

    ax.set_xticks(np.arange(-0.5, 7, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, num_weeks, 1), minor=True)
    ax.grid(which="minor", color="0.2", linestyle="-", linewidth=10)

    ax.tick_params(which="minor", size=0)

    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.patch.set_facecolor("0.2")
    ax.set_facecolor("0.2")

    ax.spines[:].set_color("0.2")

    ax.set_title("PROGRESS", color="wheat")

    plt.show()

def append_data_to_file(number):
    current_datetime = today
    last_date = None
    file_path = stable_daily_log
    with open(file_path, "r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            if row:
                last_date = row[0]

    if last_date and last_date.split()[0] == datetime.now().strftime("%Y-%m-%d"):
        updated_rows = []
        with open(file_path, "r", newline="") as file:
            reader = csv.reader(file)
            for row in reader:
                if row and row[0].split()[0] == datetime.now().strftime("%Y-%m-%d"):
                    row[1] = str(number)
                updated_rows.append(row)

        with open(file_path, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(updated_rows)
    else:
        with open(file_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([current_datetime, number])

def plot_data_and_rate(data):
    fig, ax = plt.subplots(figsize=(10, 6))
    dates, numbers = zip(*data)
    numbers = [number if not np.isnan(number) else 0 for number in numbers]
    cumulative_sum = np.cumsum(numbers)
    cumulative_average = cumulative_sum / (np.arange(len(numbers)) + 1)
    remain_days = (
        datetime.strptime(config["end_date"], "%Y-%m-%d %H:%M:%S") - today
    ).days
    required_rate = [(500 - cumulative_sum[i]) / (90-i+1) for i in range(len(cumulative_sum))]

    max_value = max(max(numbers), max(required_rate), max(cumulative_average)) + 2

    ax.plot(dates, numbers, color="yellow", marker="o", linestyle="-", label="Numbers")
    ax.plot(
        dates,
        required_rate,
        color="skyblue",
        marker="o",
        linestyle="-",
        label="Required Rate",
    )
    ax.plot(
        dates,
        cumulative_average,
        color="orange",
        marker="o",
        linestyle="-",
        label="Cumulative Average",
    )

    ax.set_xlabel("Date", color="white")
    ax.set_ylabel("Value", color="white")
    ax.tick_params(axis="x", colors="white")
    ax.tick_params(axis="y", colors="white")
    ax.legend(loc="upper left")
    ax.set_title("Required Rate, and Cumulative Average Over Time", color="wheat")
    ax.set_ylim([0, max_value])
    ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=len(dates) // 7 + 1))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.patch.set_facecolor("0.2")
    ax.set_facecolor("0.2")

    plt.show()

def set_config(config_file):
    data_config = {}
    target = input("Enter target number of questions:")
    data_config["target"] = target
    data_config["start_date"] = str(today)
    end_date = input("Enter end date:(YYYY-MM-DD)")
    end_date += " 00:00:00"
    data_config["end_date"] = end_date
    write_dict_to_file(config_file, data_config)


def reset_data(data_file,stable_daily_log):
    data_dict = {"date": str(today), "total_ques": "0", "today_ques": "0"}
    write_dict_to_file(data_file, data_dict)
    with open(stable_daily_log, "w") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "number"])

def write_dict_to_file(file_path, data_dict):
    try:
        with open(file_path, 'w') as json_file:
            json.dump(data_dict, json_file)  
    except Exception as e:
        print(f"An error occurred: {e}")

def update_data():
    last_date = master_data["date"]
    last_date = datetime.strptime(last_date, "%Y-%m-%d %H:%M:%S")
    if (today - last_date).days != 0:
        master_data["date"] = str(today)
        master_data["today_ques"] = "0"
        write_dict_to_file(data_file, master_data)

def print_helper():
    print("Date ", today)
    date1 = datetime.strptime(config["end_date"], "%Y-%m-%d %H:%M:%S")
    date_del = date1 if date1<today else today
    print("current number of tasks completed:", master_data["total_ques"])
    print(
        "Completed percent - remaining percent:",
        (int(master_data["total_ques"]) / int(config["target"])) * 100,
        "% -",
        100 - (int(master_data["total_ques"]) / int(config["target"])) * 100,
        "%",
    )
    start_date = datetime.strptime(config["start_date"], "%Y-%m-%d %H:%M:%S")
    days_passed = (date_del - start_date).days
    remain_days = (
        datetime.strptime(config["end_date"], "%Y-%m-%d %H:%M:%S") - date_del
    ).days
    remain_days = remain_days if remain_days > 0 else 1
    print(
        "Average rate: "
        + str(abs(int(master_data["total_ques"]) / days_passed if days_passed != 0 else 1))
        + " tasks/day"
    )
    print(
        "Required rate: "
        + str((int(config["target"]) - int(master_data["total_ques"])) / (remain_days))
        + " tasks/day"
    )
    print("Today questions: " + str(master_data["today_ques"]))
    print("Target questions: " + str(config["target"]))
    print("Days remaining: " + str(remain_days))
    print("Days passed: " + str(days_passed))
    progress_bar((int(master_data["total_ques"]) / int(config["target"])) * 100)

def populate_configs():
    master = read_file_as_dict(master_file)
    if master["default"] is not None:
        name = master["default"]
        config_file = "."+name+"_config"
        data_file = "."+name+"_data"
        stable_daily_log = name+"_daily_log.csv"
        return config_file, data_file, stable_daily_log
    return None,None,None    

def show_message():
    root = tk.Tk()
    root.title("Congratulations")
    root.geometry("1200x200")

    label = tk.Label(root, text="WOW!!! You have already completed the target successfully!", 
                     font=("Helvetica", 24), padx=20, pady=20)
    label.pack(expand=True)
    root.mainloop()

def parse_args():
    args = {}
    for i in range(1, len(sys.argv)):
        if (sys.argv[i].startswith("--") or sys.argv[i].startswith("-")) and sys.argv[i] not in ARGS:
            print("Invalid argument")
            sys.exit(0)
    for i in range(1, len(sys.argv)):
        if sys.argv[i].startswith("--"):
            key = sys.argv[i]
            value = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
            args[key] = value
        elif sys.argv[i].startswith("-"):
            key = sys.argv[i]
            args[key] = True
    return args

def completed_call():
    print_helper()
    show_message_process = multiprocessing.Process(target=show_message)
    data = read_data_from_file(stable_daily_log)
    heatmap_process = multiprocessing.Process(
        target=plot_data_and_rate, args=(data,)
    )
    graph_process = multiprocessing.Process(
        target=create_month_heat_map, args=(data,)
    )
    heatmap_process.start()
    graph_process.start()
    show_message_process.start()
    heatmap_process.join()
    graph_process.join()
    show_message_process.join()
    sys.exit(0)

if os.path.exists(master_file) == False:
    master = {"default":None, "list":[]}
    write_dict_to_file(master_file, master)

args = parse_args()
pop = populate_configs()
config_file = pop[0]
data_file = pop[1]
stable_daily_log = pop[2]

if "--file" in args.keys():
    name = args["--file"]
    config_file = "."+name+"_config"
    data_file = "."+name+"_data"
    stable_daily_log = name+"_daily_log.csv"

    if os.path.exists(config_file) == False:
        set_config(config_file=config_file)
    if os.path.exists(data_file) == False:
        reset_data(data_file=data_file,stable_daily_log=stable_daily_log)

    config = read_file_as_dict(config_file)
    master_data = read_file_as_dict(data_file)
    update_data()


if "--create" in args.keys():
    name = args["--create"]
    config_file = "."+name+"_config"
    data_file = "."+name+"_data"
    stable_daily_log = name+"_daily_log.csv"
    master = read_file_as_dict(master_file)

    if(name in master["list"]):
        print(f"Task {name} already exists try new name")
        sys.exit(0)

    set_config(config_file=config_file)

    if(input("Do you want to set this is default task (y/n)?")=='y'):
        master["default"]=name
    master["list"].append(name)
    write_dict_to_file(master_file,master)
    sys.exit(0)

if "--set-default" in args.keys():
    name = args["--set-default"]
    master = read_file_as_dict(master_file)
    if(name not in master["list"]):
        print(f"Task {name} does not exist")
        sys.exit(0)
    master["default"]=name
    write_dict_to_file(master_file,master)
    sys.exit(0)

if "--list" in args.keys():
    master = read_file_as_dict(master_file)
    print(master["list"])
    sys.exit(0)

if "--delete" in args.keys():
    name = args["--delete"]
    master = read_file_as_dict(master_file)
    if(name not in master["list"]):
        print(f"Task {name} does not exist")
        sys.exit(0)
    master["list"].remove(name)
    if("default" in master.keys() and master["default"]==name):
        master["default"]=""
    if os.path.exists("."+name+"_config"):
        os.remove("."+name+"_config")
    if os.path.exists("."+name+"_data"):
        os.remove("."+name+"_data")
    if os.path.exists(name+"_daily_log.csv"):
        os.remove(name+"_daily_log.csv")
    write_dict_to_file(master_file,master)
    print("Task deleted successfully")
    sys.exit(0)

if "--default" in args.keys():
    name = args["--default"]
    master = read_file_as_dict(master_file)
    print("Default task:",master["default"])
    sys.exit(0)

if config_file is not None and os.path.exists(config_file) == False:
    set_config(config_file=config_file)
if data_file is not None and os.path.exists(data_file) == False:
    reset_data(data_file=data_file,stable_daily_log=stable_daily_log)
master_data = read_file_as_dict(data_file)
config = read_file_as_dict(config_file)

if "-r" in args.keys():
    set_config(config_file=config_file)
    print("Config file updated successfully")
    sys.exit(0)
elif "-s" in args.keys():
    if master_data["date"] != str(today):
        master_data["date"] = str(today)
        master_data["today_ques"] = "0"
        write_dict_to_file(data_file, master_data)
        append_data_to_file(master_data["today_ques"])
    if(master_data["total_ques"] == config["target"]):
        show_message_process = multiprocessing.Process(target=show_message)
        show_message_process.start()
        show_message_process.join()
    print_helper()
    append_data_to_file(master_data["today_ques"])
    data = read_data_from_file(stable_daily_log)
    heatmap_process = multiprocessing.Process(
        target=plot_data_and_rate, args=(data,)
    )
    graph_process = multiprocessing.Process(
        target=create_month_heat_map, args=(data,)
    )
    heatmap_process.start()
    graph_process.start()
    heatmap_process.join()
    graph_process.join()
    sys.exit(0)

if(int(master_data["total_ques"]) >= int(config["target"])):
    completed_call()
if master_data["date"] != str(today):
    master_data["date"] = str(today)
    master_data["today_ques"] = "0"
    write_dict_to_file(data_file, master_data)
    append_data_to_file(master_data["today_ques"])
master_data["today_ques"] = str(int(master_data["today_ques"]) + 1)
master_data["total_ques"] = str(int(master_data["total_ques"]) + 1)
if(int(master_data["total_ques"]) >= int(config["target"])):
    completed_call()
print_helper()
write_dict_to_file(data_file, master_data)
append_data_to_file(master_data["today_ques"])
