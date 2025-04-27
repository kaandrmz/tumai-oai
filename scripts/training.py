import argparse
import requests
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.agents.student_agent import StudentAgent
from app.models import ChatMessage
from app.config import FASTAPI_URL as DEFAULT_FASTAPI_URL

def run_simulation(teacher_url: str, task_id: int, max_turns: int = 4, session_id_arg: int | None = None):
    """Runs a single simulation conversation."""
    print(f"Starting simulation for task ID: {task_id} against URL: {teacher_url}")
    if session_id_arg:
        print(f"Using provided session ID: {session_id_arg}")

    my_agent = StudentAgent(teacher_url=teacher_url)

    # 1. Start Session
    try:
        print("Starting session...")
        session_data = my_agent.start_session(task_id, session_id=session_id_arg)
        if not session_data or "session_id" not in session_data or "history" not in session_data:
            print(f"Error: Could not start session. Response: {session_data}")
            return
        session_id = session_data["session_id"]
        initial_history = session_data["history"] # History might already contain the first teacher message
        # If a session_id was provided, verify it matches the one returned by the server
        if session_id_arg is not None and session_id_arg != session_id:
             print(f"Warning: Server returned session ID {session_id}, which differs from provided ID {session_id_arg}. Using server's ID.")
        
        print(f"Session started with ID: {session_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to the server at {teacher_url}: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred during session start: {e}")
        return

    # Initialize conversation history from session data
    history = []
    initial_teacher_message = None
    for msg_data in initial_history:
         # Handle both dict and object possibilities from the API
        if isinstance(msg_data, dict) and "role" in msg_data and "content" in msg_data:
            msg = ChatMessage(**msg_data)
            history.append(msg)
            if msg.role == 'teacher':
                initial_teacher_message = msg.content
        elif hasattr(msg_data, 'role') and hasattr(msg_data, 'content'):
             history.append(msg_data) # Assumes it's already a ChatMessage object
             if msg_data.role == 'teacher':
                initial_teacher_message = msg_data.content
        else:
            print(f"Warning: Skipping invalid message format in initial history: {msg_data}")

    if initial_teacher_message:
        print(f"Initial Teacher Message: {initial_teacher_message}")
    else:
        # If no teacher message, add a placeholder or fetch initial context if needed
        # For now, we'll rely on the student generating the first substantial turn
        print("No initial teacher message found in session start history.")
        # Example: Add a placeholder if your flow requires it
        # initial_message = ChatMessage(role="user", content="Please provide the patient's initial complaint.")
        # history.insert(0, initial_message) # Prepend if needed

    conversation_result = {"session_id": session_id, "history": history}

    # 2. Run Conversation Loop
    print("\n--- Starting Conversation ---")
    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")

        # Check if it's time for diagnosis (e.g., after 3 student-teacher exchanges)
        # The condition turn >= 3 implies 3 full exchanges (S->T, T->S) have occurred.
        if turn >= max_turns -1: # Let's generate diagnosis on the last turn
             # Generate final diagnosis
            try:
                print("Generating final diagnosis...")
                diagnosis = my_agent.generate_diagnosis(history)
                print(f"\n--- FINAL DIAGNOSIS ---")
                print(f"Doctor: {diagnosis}")

                # Add diagnosis to history (as teacher role for consistency)
                diagnosis_message = ChatMessage(role="teacher", content=diagnosis)
                history.append(diagnosis_message)
                conversation_result = {"session_id": session_id, "history": history}
                break # End the conversation after diagnosis
            except Exception as e:
                print(f"Error generating diagnosis: {e}")
                # Decide how to handle: break, continue, log?
                break

        # Generate and print student reply
        try:
            print("Student generating reply...")
            student_reply = my_agent.generate_reply(history)
            print(f"Student: {student_reply}")

            # Add student reply to history
            student_message = ChatMessage(role="student", content=student_reply)
            history.append(student_message)
        except Exception as e:
            print(f"Error generating student reply: {e}")
            # Decide how to handle: break, continue with dummy reply?
            break # Stop simulation on error for now

        # Send history to teacher for evaluation and next response
        try:
            print("Sending reply to teacher...")
            response_data = my_agent.send_reply(session_id, history)

            # Check for errors in response
            if "error" in response_data:
                print(f"Error received from teacher API: {response_data['error']}")
                # Optional: Implement retry or specific error handling
                # For now, we'll break the loop on API errors during evaluation
                break
            else:
                 # Update history from response
                if "history" in response_data:
                    response_history_raw = response_data["history"]
                    current_msg_count = len(history)

                    # Normalize response history items to ChatMessage objects
                    response_history_processed = []
                    for msg_data in response_history_raw:
                         if isinstance(msg_data, dict) and "role" in msg_data and "content" in msg_data:
                            response_history_processed.append(ChatMessage(**msg_data))
                         elif hasattr(msg_data, 'role') and hasattr(msg_data, 'content'):
                             response_history_processed.append(msg_data) # Assumes it's already a ChatMessage object
                         else:
                             print(f"Warning: Skipping invalid message format in response history: {msg_data}")


                    # Check if new messages were added
                    if len(response_history_processed) > current_msg_count:
                        # Find the new message(s) (usually the last one)
                        new_messages = response_history_processed[current_msg_count:]
                        for teacher_msg in new_messages:
                             if teacher_msg.role == "teacher": # Ensure it's the teacher's response
                                print(f"Teacher: {teacher_msg.content}")
                                history.append(teacher_msg) # Add the actual new message object
                             else:
                                 # Handle unexpected roles if necessary
                                 print(f"Warning: Received non-teacher message in response: Role={teacher_msg.role}")
                                 history.append(teacher_msg) # Add anyway for completeness?

                    else:
                        print("Teacher API did not return a new message.")
                        # Decide: break, continue, or simulate a generic teacher response?
                        # Let's break for now if no new message is received.
                        break

                # Check if session ended by the teacher
                if response_data.get("is_end", False):
                    print("\nSession ended by the teacher.")
                    break

        except requests.exceptions.RequestException as e:
             print(f"Error connecting to the teacher API during send_reply: {e}")
             break
        except Exception as e:
            print(f"An unexpected error occurred during send_reply: {e}")
            break # Stop simulation on error


    # 3. Print Summary
    print("\n--- Conversation Summary ---")
    final_history = conversation_result['history']
    print(f"Total messages: {len(final_history)}")
    print("\nFinal conversation state:")
    for i, message in enumerate(final_history):
        role = message.role.capitalize()
        # Handle potential non-string content if necessary
        content_preview = str(message.content)[:70] + "..." if len(str(message.content)) > 70 else str(message.content)
        print(f"{i + 1}. {role}: {content_preview}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a student-teacher simulation.")
    parser.add_argument(
        "--url",
        type=str,
        help="URL of the FastAPI teacher service"
    )
    parser.add_argument(
        "--task_id",
        type=int,
        required=True,
        help="Task ID for the simulation session"
    )
    parser.add_argument(
        "--session_id",
        type=int,
        default=None,
        help="Optional session ID to use/reuse"
    )
    parser.add_argument(
        "--max_turns",
        type=int,
        default=4,
        help="Maximum number of conversation turns (default: 4)"
    )

    args = parser.parse_args()

    # Basic validation
    if not args.url:
        print("Error: FastAPI URL cannot be empty.")
        sys.exit(1)
    if args.task_id <= 0:
        print("Error: Task ID must be a positive integer.")
        sys.exit(1)
    if args.max_turns <= 0:
        print("Error: Max turns must be a positive integer.")
        sys.exit(1)


    run_simulation(
        teacher_url=args.url, 
        task_id=args.task_id, 
        max_turns=args.max_turns,
        session_id_arg=args.session_id # Pass the parsed session_id
    )

    print("\nSimulation finished.")
