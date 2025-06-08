import MeetingLogs as ml

doc_url = "https://docs.google.com/document/d/e/2PACX-1vQPgH-0mkjK0T9Yq3IkiGqGq-KOwJEoGLpuifOaqLpk-R0H0heVxIE9kJUzQaS_0HVOqEzg4nAlfQnY/pub"
logs = ml.extract_meeting_logs(doc_url)

print(" Extracted Meeting Logs:\n")
for log in logs:
    print(f"- {log}")
