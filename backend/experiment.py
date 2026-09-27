import json

# A sample JSON-like dictionary defining the experiment protocol
SAMPLE_EXPERIMENT = {
    "experiment_id": "container_handling_101",
    "name": "Sample Container Handling Procedure",
    "steps": [
        {
            "id": "step_1",
            "description": "Retrieve the sample container from the storage rack.",
            "expected_activity": "retrieved bottle"
        },
        {
            "id": "step_2",
            "description": "Transfer the sample container into the workstation zone.",
            "expected_activity": "transferred bottle"
        },
        {
            "id": "step_3",
            "description": "Set the sample container down securely at the workstation.",
            "expected_activity": "placed bottle"
        },
        {
            "id": "step_4",
            "description": "Pick up and return the sample container back to the storage rack.",
            "expected_activity": "returned bottle"
        }
    ]
}

class ExperimentStateMachine:
    def __init__(self, experiment_protocol):
        self.protocol = experiment_protocol
        self.steps = self.protocol["steps"]
        self.current_step_index = 0
        self.completed = False
        self.completed_steps = []
        self.last_violation = None
        
    def reset(self):
        self.current_step_index = 0
        self.completed_steps = []
        self.completed = False
        self.last_violation = None

    def get_state(self):
        current = self.steps[self.current_step_index] if not self.completed else None
        next_step = self.steps[self.current_step_index + 1] if self.current_step_index + 1 < len(self.steps) else None
        return {
            "completed": self.completed,
            "current_step": current,
            "next_step": next_step,
            "completed_steps": self.completed_steps,
            "last_violation": self.last_violation,
            "total_steps": len(self.steps),
            "all_steps": self.steps
        }
        
    def advance(self, activity_label):
        """
        Takes a detected activity label and advances the state machine.
        Returns a dict indicating success, completion, or a specific violation.
        """
        if self.completed:
            return {"status": "error", "message": "Experiment is already completed.", "type": "completed"}
            
        expected_step = self.steps[self.current_step_index]
        
        # 1. Correct sequence: Matches the expected next activity
        if activity_label == expected_step["expected_activity"]:
            self.completed_steps.append(expected_step["id"])
            self.current_step_index += 1
            
            # Clear violation on success
            self.last_violation = None
            
            if self.current_step_index >= len(self.steps):
                self.completed = True
                return {"status": "completed", "message": "Experiment finished successfully!"}
            return {
                "status": "ok", 
                "message": f"Completed step: {expected_step['description']}", 
                "next_step": self.steps[self.current_step_index]
            }
            
        # 2. Check for repeated step
        for step in self.steps[:self.current_step_index]:
            if activity_label == step["expected_activity"]:
                self.last_violation = {"type": "repeated", "message": f"Repeated step detected: '{step['description']}'"}
                return {"status": "error", "message": self.last_violation["message"], "type": "repeated"}
                
        # 3. Check for skipped or out-of-sequence steps
        for i in range(self.current_step_index + 1, len(self.steps)):
            if activity_label == self.steps[i]["expected_activity"]:
                if i == self.current_step_index + 1:
                    self.last_violation = {"type": "skipped", "message": f"Skipped step: You missed '{expected_step['description']}'"}
                    return {"status": "error", "message": self.last_violation["message"], "type": "skipped"}
                else:
                    self.last_violation = {"type": "out_of_sequence", "message": f"Out of sequence: Jumped to '{self.steps[i]['description']}'"}
                    return {"status": "error", "message": self.last_violation["message"], "type": "out_of_sequence"}
                    
        # 4. Completely unexpected activity
        self.last_violation = {"type": "unexpected", "message": f"Unexpected activity detected: '{activity_label}'"}
        return {"status": "error", "message": self.last_violation["message"], "type": "unexpected"}

# Global instance used across modules
experiment_state = ExperimentStateMachine(SAMPLE_EXPERIMENT)
