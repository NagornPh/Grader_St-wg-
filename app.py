import streamlit as st
import subprocess
import time
import os
import requests
import psutil

def compile_cpp(source_path, output_path):
    command = ["g++", "-std=c++17", source_path, "-o", output_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout.decode(), result.stderr.decode()

def download_file(url, destination):
    response = requests.get(url)
    with open(destination, 'wb') as f:
        f.write(response.content)

def get_memory_usage(pid):
    try:
        process = psutil.Process(pid)
        memory_info = process.memory_info()
        return memory_info.rss
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None

def run_executable(executable_path, input_file, runtime_limit, memory_limit):
    try:
        if not os.path.exists(input_file):
            st.error(f"Input file {input_file} does not exist.")
            return "", "Input file does not exist.", None, None, -1
        
        start_time = time.time()
        with open(input_file, 'r') as f:
            process = subprocess.Popen([executable_path], stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pid = process.pid
        
        # Communicate with timeout
        try:
            stdout, stderr = process.communicate(timeout=runtime_limit)
            returncode = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            returncode = -1
        
        end_time = time.time()
        runtime = end_time - start_time
        
        # Get memory usage
        max_memory = get_memory_usage(pid)
        
        return stdout.decode(), stderr.decode(), runtime, max_memory, returncode
    
    except Exception as e:
        return "", f"Error: {str(e)}", 0, None, -1

def grade(output, expected_output_file, runtime, max_memory, runtime_limit, memory_limit):
    if runtime is None or max_memory is None:
        return 0  # Return 0 grade if runtime or max_memory is None
    
    with open(expected_output_file, 'r') as f:
        expected_output = f.read().strip()
    
    score = 1 if output.strip() == expected_output.strip() and runtime <= runtime_limit and max_memory <= memory_limit else 0
    return score

st.title("C++ Code Grader")

problems = {
    "Pointing": {
        "test_cases": 2,
        "rt": 10,  # Runtime limit in seconds
        "mem": 50 * 1024 * 1024  # Memory limit in bytes
    },
    "Problem 2": {
        "test_cases": 0,
        "rt": 1,  # Runtime limit in seconds
        "mem": 50 * 1024 * 1024  # Memory limit in bytes
    }
    # Add more problems here
}

selected_problem = st.selectbox("Select a problem", list(problems.keys()))

st.write(f"### {selected_problem}")

uploaded_file = st.file_uploader("Upload your C++ file", type=["cpp"])

# Button to compile and run
if st.button("Compile and Run"):
    if uploaded_file is not None:
        source_code = uploaded_file.read()
        source_path = "submitted_code.cpp"
        executable_path = "./submitted_code"

        with open(source_path, "wb") as f:
            f.write(source_code)

        compile_returncode, compile_stdout, compile_stderr = compile_cpp(source_path, executable_path)

        # Print compilation output for debugging
        st.write(f"Compilation stdout:\n{compile_stdout}")
        st.write(f"Compilation stderr:\n{compile_stderr}")

        if compile_returncode != 0:
            st.error(f"Compilation failed:\n{compile_stderr}")
        else:
            total_grade = 0
            total_test_cases = problems[selected_problem]["test_cases"]

            for idx in range(1, total_test_cases + 1):
                input_url = f"https://github.com/PakinDioxide/Grader_St/raw/main/Problems/{selected_problem}/{idx}.in"
                expected_output_file = f"https://github.com/PakinDioxide/Grader_St/raw/main/Problems/{selected_problem}/{idx}.out"

                # Download input file
                input_file = f"https://github.com/PakinDioxide/Grader_St/raw/main/Problems/{selected_problem}/{idx}.in"
                download_file(input_url, input_file)

                output, errors, runtime, max_memory, returncode = run_executable(executable_path, input_file, problems[selected_problem]["rt"], problems[selected_problem]["mem"])

                grade_score = grade(output, expected_output_file, runtime, max_memory, problems[selected_problem]["rt"], problems[selected_problem]["mem"])
                total_grade += grade_score

                st.write(f"### Test Case {idx}")
                st.write(f"Input File: {input_file}")
                st.write(f"Expected Output File: {expected_output_file}")
                st.write(f"Output: {output}")
                st.write(f"Errors: {errors}")
                st.write(f"Runtime: {runtime} seconds")
                st.write(f"Max Memory: {max_memory} Megabytes")
                st.write(f"Return Code: {returncode}")
                st.write(f"Grade: {grade_score}/1")
                st.write("---")

            final_grade = total_grade / total_test_cases
            st.write(f"## Final Grade: {final_grade}/{1 * total_test_cases}")

            # Clean up
            if os.path.exists(source_path):
                os.remove(source_path)
            if os.path.exists(executable_path):
                os.remove(executable_path)
