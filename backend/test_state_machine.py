from experiment import ExperimentStateMachine, SAMPLE_EXPERIMENT

def run_test(scenario_name, activities):
    print(f"\n{'='*40}")
    print(f"--- Running Scenario: {scenario_name} ---")
    print(f"{'='*40}")
    
    sm = ExperimentStateMachine(SAMPLE_EXPERIMENT)
    current_step = sm.steps[sm.current_step_index]
    
    print(f"Initial expected: {current_step['description']} ({current_step['expected_activity']})")
    
    for act in activities:
        print(f"\n-> Emitted Activity: '{act}'")
        result = sm.advance(act)
        
        if result["status"] == "ok":
            print(f"   [SUCCESS] {result['message']}")
            print(f"   [NEXT EXPECTED] {result['next_step']['description']} ({result['next_step']['expected_activity']})")
        elif result["status"] == "completed":
            print(f"   [COMPLETED] {result['message']}")
        else:
            print(f"   [VIOLATION] Type: {result['type'].upper()} | {result['message']}")

if __name__ == "__main__":
    # Scenario 1: Perfect execution
    perfect_activities = [
        "reaching bottle",
        "picking bottle",
        "reaching laptop",
        "releasing bottle",
        "releasing laptop"
    ]
    run_test("Perfect Execution", perfect_activities)
    
    # Scenario 2: Skipped step (missed picking bottle)
    skipped_activities = [
        "reaching bottle",
        "reaching laptop", 
    ]
    run_test("Skipped Step", skipped_activities)
    
    # Scenario 3: Repeated step
    repeated_activities = [
        "reaching bottle",
        "picking bottle",
        "reaching bottle", # Doing step 1 again
    ]
    run_test("Repeated Step", repeated_activities)
    
    # Scenario 4: Out of sequence (skipping multiple steps)
    oos_activities = [
        "reaching bottle",
        "releasing bottle", # Jumped straight to step 4
    ]
    run_test("Out of Sequence", oos_activities)
    
    # Scenario 5: Unexpected random activity
    unexpected_activities = [
        "reaching bottle",
        "picking scissors", # Not in protocol
    ]
    run_test("Unexpected Activity", unexpected_activities)
