import os
import sys
import subprocess

def run_command(command, description):
    print(f"\nExecuting: {description}")
    print(f"Command: {' '.join(command)}")
    print("-" * 58)
    try:
        subprocess.run(command, check=False)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError executing command: {e}")
    input("\nPress Enter to return to menu...")

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("==========================================================")
        print("              自媒体自动化工具 (Media Skills Launcher)")
        print("==========================================================")
        print("1. 生成并发布到小红书")
        print("2. 一键全自动 (基于 config.json)")
        print("3. 退出")
        print("==========================================================")
        
        choice = input("请选择一个选项 (1-3): ").strip()
        
        if choice == "1":
            print("\n[1] 小红书自动化")
            input_path = input("请输入输入路径 (文件或目录) [默认: output/articles]: ").strip() or "output/articles"
            
            print("\n选择模式:")
            print("1. 空跑测试 (仅生成内容)")
            print("2. 发布 (实时发布)")
            mode = input("请选择模式 (1/2): ").strip()
            
            cmd = [sys.executable, "xiaohongshu_skill/main.py", "--input", input_path]
            desc = "Xiaohongshu Dry Run"
            
            if mode == "2":
                desc = "Xiaohongshu Publish"
                show_ui = input("\n显示浏览器界面? (y/n) [默认: n]: ").strip().lower()
                if show_ui == 'y':
                    cmd.append("--non-headless")
            else:
                cmd.append("--dry-run")
                
            run_command(cmd, desc)
            
        elif choice == "2":
            if not os.path.exists("config.json"):
                print("\n错误: 未找到 config.json 配置文件。")
                input("Press Enter to continue...")
                continue
            run_command([sys.executable, "auto_run.py"], "Auto Run")
            
        elif choice == "3":
            print("正在退出...")
            break
        else:
            input("无效选项，请重试。Press Enter...")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass
    main()
