import re
import matplotlib.pyplot as plt
import os

def parse_wcrt_output(file_path):
    """
    Parse the wcrt_output.txt file and return a list of dictionaries.
    """
    results = []
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Skip header
    start_parsing = False
    for line in lines:
        line = line.strip()
        if line.startswith('Case') and 'ID' in line:
            start_parsing = True
            continue
        if line.startswith('-') and start_parsing:
            continue
        if start_parsing and line:
            # Split by multiple spaces
            parts = re.split(r'\s+', line)
            if len(parts) >= 7:
                case = parts[0]
                stream_id = int(parts[1])
                name = parts[2]
                pcp = int(parts[3])
                deadline_us = int(parts[4])
                wcrt_us = float(parts[5])
                status = parts[6]
                results.append({
                    'case': case,
                    'stream_id': stream_id,
                    'name': name,
                    'pcp': pcp,
                    'deadline_us': deadline_us,
                    'wcrt_us': wcrt_us,
                    'status': status
                })
    return results

def group_by_case(results):
    """
    Group results by case.
    """
    cases = {}
    for row in results:
        case = row['case']
        if case not in cases:
            cases[case] = []
        cases[case].append(row)
    return cases

def plot_case(case_name, streams):
    """
    Create a bar plot for a test case.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    stream_names = [s['name'] for s in streams]
    wcrt_values = [s['wcrt_us'] for s in streams]
    deadlines = [s['deadline_us'] for s in streams]
    statuses = [s['status'] for s in streams]

    colors = ['green' if status == 'OK' else 'red' for status in statuses]

    x = range(len(stream_names))

    ax.bar(x, wcrt_values, color=colors, alpha=0.7, label='WCRT')
    ax.plot(x, deadlines, 'b--', marker='o', label='Deadline')

    ax.set_xticks(x)
    ax.set_xticklabels(stream_names, rotation=45, ha='right')
    ax.set_ylabel('Time (μs)')
    ax.set_title(f'WCRT Analysis for {case_name}')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Save the plot
    safe_name = case_name.replace('/', '_').replace('\\', '_')
    output_dir = 'plots'
    os.makedirs(output_dir, exist_ok=True)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{safe_name}.png')
    plt.close()

def main():
    file_path = 'wcrt_output.txt'
    results = parse_wcrt_output(file_path)
    cases = group_by_case(results)

    for case_name, streams in cases.items():
        plot_case(case_name, streams)

    print(f"Generated plots for {len(cases)} test cases in 'plots/' directory.")

if __name__ == '__main__':
    main()