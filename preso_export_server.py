#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreSO Export Server
===================
ブラウザからExportされた顧客データを受信し、JSONファイルに保存するローカルサーバー。
Phase2でMDSへの転送処理を追加予定。

使い方:
  python preso_export_server.py

依存: なし（Python標準ライブラリのみ）
"""

import json
import os
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ===== 設定 =====
HOST = 'localhost'
PORT = 5000
EXPORT_DIR = 'exports'

# ===== MDS設定 (Phase2で使用) =====
# MDS_API_URL = ''       # MDSエンドポイントURL
# MDS_API_KEY = ''       # APIキー
# MDS_AUTH_TYPE = ''     # 認証方式 (basic, bearer, apikey)


class ExportHandler(BaseHTTPRequestHandler):
    """PreSOデータ受信ハンドラ"""

    def do_OPTIONS(self):
        """CORS プリフライトリクエスト対応"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Export データ受信"""
        if self.path == '/export':
            self._handle_export()
        else:
            self.send_error(404, 'Not Found')

    def do_GET(self):
        """ヘルスチェック"""
        if self.path == '/':
            self._send_json(200, {'status': 'running', 'version': '1.0'})
        else:
            self.send_error(404, 'Not Found')

    def _handle_export(self):
        """ExportデータをJSONファイルに保存"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json(400, {'status': 'error', 'message': 'リクエストボディが空です'})
                return

            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            # バリデーション
            required = ['firstName', 'lastName', 'phone', 'postCode', 'address']
            missing = [f for f in required if not data.get(f)]
            if missing:
                self._send_json(400, {
                    'status': 'error',
                    'message': '必須フィールドが不足: ' + ', '.join(missing)
                })
                return

            # 保存
            os.makedirs(EXPORT_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            postal = data.get('postCode', 'unknown').replace('-', '')
            filename = 'preso_export_{}_{}.json'.format(postal, timestamp)
            filepath = os.path.join(EXPORT_DIR, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print('[EXPORT] 保存完了: {} ({})'.format(filepath, data.get('postCode')))

            # Phase2: ここでMDSへ転送処理を追加
            # mds_result = send_to_mds(data)

            self._send_json(200, {
                'status': 'ok',
                'message': 'データを {} に保存しました'.format(filepath),
                'file': filepath
            })

        except json.JSONDecodeError:
            self._send_json(400, {'status': 'error', 'message': 'JSONの解析に失敗しました'})
        except Exception as e:
            self._send_json(500, {'status': 'error', 'message': str(e)})

    def _send_json(self, code, data):
        """JSON レスポンス送信"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        """ログ出力"""
        print('[{}] {}'.format(
            datetime.datetime.now().strftime('%H:%M:%S'),
            format % args
        ))


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    server = HTTPServer((HOST, PORT), ExportHandler)
    print('=' * 50)
    print('  PreSO Export Server')
    print('  http://{}:{}'.format(HOST, PORT))
    print('  Export先: ./{}/'.format(EXPORT_DIR))
    print('  Ctrl+C で停止')
    print('=' * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nサーバーを停止しました')
        server.server_close()


if __name__ == '__main__':
    main()
