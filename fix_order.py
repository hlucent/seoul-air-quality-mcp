import io

with io.open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

marker = 'if __name__ == "__main__":'
idx = content.index(marker)

before = content[:idx]
after = content[idx:]

# after 안에서 mcp.run(...) 다음 줄부터 있는 세 번째 도구 코드를 분리
run_end_marker = "mcp.run(transport=\"streamable-http\", host=\"0.0.0.0\", port=port)"
run_idx = after.index(run_end_marker) + len(run_end_marker)

main_block = after[:run_idx]
tool_block = after[run_idx:]

new_content = before + tool_block.strip("\n") + "\n\n" + main_block + "\n"

with io.open("main.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("재배치 완료")
