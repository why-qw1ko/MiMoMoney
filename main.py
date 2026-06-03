import os
import json
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# 配置文件
CONFIG_FILE = "mimo_config.json"

class MimoTool:
    def __init__(self):
        self.cookies = self.load_config()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self, cookie_dict):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookie_dict, f, indent=4)
        self.cookies = cookie_dict

    def browser_login(self):
        print("\n[系统] 正在启动登录窗口...")
        with sync_playwright() as p:
            browser_executable = None
            for channel in ["chrome", "msedge"]:
                try:
                    browser = p.chromium.launch(headless=False, channel=channel)
                    browser_executable = channel
                    break
                except:
                    continue

            if not browser_executable:
                print("❌ [错误] 没找到 Chrome 或 Edge 浏览器，请先安装其中之一。")
                return False

            context = browser.new_context()
            page = context.new_page()
            page.goto("https://platform.xiaomimimo.com/console/usage")

            print("[系统] 等待登录中... (请在浏览器窗口完成小米账号登录)")

            try:
                # 等待跳转回控制台
                page.wait_for_url("**/console/**", timeout=120000)
                print("[系统] 检测到登录成功！正在同步凭证...")

                cookies = context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}

                self.save_config(cookie_dict)
                browser.close()
                return True
            except Exception as e:
                print(f"❌ [错误] 登录超时或失败: {e}")
                browser.close()
                return False

    def fetch_data(self):
        """拉取 Mimo 所有相关数据"""
        if not self.cookies:
            return None

        headers = {
            "Content-Type": "application/json",
            "x-timezone": "Asia/Shanghai",
            "Referer": "https://platform.xiaomimimo.com/console/usage"
        }
        
        base_url = "https://platform.xiaomimimo.com/api/v1"
        try:
            # 获取个人信息
            r_p = self.session.get(f"{base_url}/userProfile", cookies=self.cookies, headers=headers, timeout=10)
            # 获取余额
            r_b = self.session.get(f"{base_url}/balance", cookies=self.cookies, headers=headers, timeout=10)
            # 获取消耗
            r_u = self.session.get(f"{base_url}/usage", cookies=self.cookies, headers=headers, timeout=10)

            p_json = r_p.json()
            b_json = r_b.json()
            u_json = r_u.json()

            if p_json.get("code") == 0 and b_json.get("code") == 0:
                return {
                    "profile": p_json['data'],
                    "balance": b_json['data'],
                    "usage": u_json['data']
                }
        except Exception:
            pass
        return None

    def print_report(self, data):
        p = data['profile']
        b = data['balance']
        u = data['usage']
        
        print("\n" + "╔" + "═" * 50 + "╗")
        print(f"║ {'MIMO API 账户状态报告':^42} ║")
        print("╠" + "═" * 50 + "╣")
        
        # 1. 用户信息
        print(f"║ [用户信息]")
        print(f"║ 👤 用户账号: {p.get('phone', 'N/A')}")
        print(f"║ 🆔 用户 ID : {p.get('userId', 'N/A')}")
        print(f"║ 📧 绑定邮箱: {p.get('email', '未绑定')}")
        print(f"║")
        
        # 2. 资金概览
        print(f"║ [资金概览]")
        print(f"║ 💰 总可用余额: {b.get('balance')} {b.get('currency')}")
        print(f"║ 💵 现金余额  : {b.get('cashBalance')} {b.get('currency')}")
        print(f"║ 🎁 赠送余额  : {b.get('giftBalance')} {b.get('currency')}")
        print(f"║")
        
        # 3. 消费统计
        cost = u.get('costUsage', {})
        print(f"║ [消费统计]")
        print(f"║ 📅 当月累计支出: {cost.get('currentMonthCost')} CNY")
        print(f"║ 📉 历史累计总额: {cost.get('totalCost')} CNY")
        print(f"║")
        
        # 4. Token 消耗详情
        tk = u.get('tokenUsage', {})
        print(f"║ [Token 消耗详情]")
        print(f"║ 📈 历史总消耗: {tk.get('totalToken', 0):,}")
        print(f"║ 📥 输入 Token: {tk.get('inputToken', 0):,}")
        print(f"║ ⚡ 命中缓存  : {tk.get('cacheToken', 0):,}")
        print(f"║ 📤 输出 Token: {tk.get('outputToken', 0):,}")
        
        print("╠" + "═" * 50 + "╣")
        print(f"║ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<29} ║")
        print("╚" + "═" * 50 + "╝")
        
        # 安全声明
        print("\n💡 [安全提示]")
        print(f" - 本工具仅在本地运行，登录凭证 (Cookie) 加密存储于: {CONFIG_FILE}")
        print(" - 请勿将该 JSON 文件发送给任何人，以免造成账号资产损失。")
        print(" - 如需切换账号或登出，请删除该文件后重新运行。\n")

    def run(self):
        # 尝试获取数据
        data = self.fetch_data()

        # 如果失败（无 token 或过期），启动浏览器登录
        if data is None:
            if self.browser_login():
                data = self.fetch_data()
            else:
                return

        # 打印结果
        if data:
            self.print_report(data)
        else:
            print("❌ 无法获取数据，请尝试重新输入 /m 或检查网络。")


def main():
    print("""
    ===========================================
               MimoAPI 增强工具 v2.0
    ===========================================
    [*] 声明：本程序不收集任何私钥或密码
    [*] 凭证存储：本地 mimo_config.json
    [*] 操作说明：输入 [/m] 查询 | [exit] 退出
    ===========================================
    """)
    tool = MimoTool()
    while True:
        try:
            cmd = input(">>> ").strip().lower()
            if cmd == "/m":
                tool.run()
            elif cmd == "exit":
                print("程序已安全退出。")
                break
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()