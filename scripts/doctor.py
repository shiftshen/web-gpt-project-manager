#!/usr/bin/env python3
"""Read-only local prerequisite checks. Never reads credentials or claims MCP connectivity."""
import json,platform,shutil,sys
from pathlib import Path

def check():
    return {'pythonSupported':sys.version_info>=(3,11),'python':platform.python_version(),
            'os':platform.system(),'skillPresent':(Path(__file__).resolve().parent.parent/'SKILL.md').is_file(),
            'webcodexCliFound':shutil.which('webcodex') is not None,
            'chromeScriptSupported':platform.system()=='Darwin' and shutil.which('osascript') is not None,
            'webcodexConnectionVerified':False,
            'next':'Read references/setup.md; Desktop can be installed without a CLI. Verify an actual project read and bootstrap probe.'}
if __name__=='__main__':
    result=check();print(json.dumps(result,ensure_ascii=True,indent=2));sys.exit(0 if result['pythonSupported'] and result['skillPresent'] else 2)
