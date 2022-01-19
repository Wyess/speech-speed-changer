#!/usr/bin/env python3

from enum import Enum
import os
import sys
import shutil
import subprocess
import wx

class AudioItem:
    def __init__(self, in_file='', speed_list=None, out_dir='', out_format=None):
        self.in_file = in_file
        self.speed_list = speed_list if speed_list else []
        self.out_dir = out_dir
        self.out_files = []
        self.out_format = out_format

        head, tail = os.path.split(self.in_file)
        base, _ = os.path.splitext(tail)
        ext = self.out_format['ext']

        self.out_files = [os.path.join(self.out_dir, f"{base}_x{speed}{ext}") for speed in speed_list]
        self.commands = []
        for out in self.out_files:
            self.commands.append([])
            self.commands[-1] = self.out_format['cmd'].split(' ')
            self.commands[-1][1:1] = ['-i', self.in_file]
            self.commands[-1].append(out)

    def __str__(self):
        s = self.in_file
        s += "\n"
        s += self.out_dir
        s += "\n"
        s += ",".join([str(i) for i in self.speed_list])
        s += "\n"
        s += "\n".join(self.out_files)
        s += "\n"
        s += str(self.out_format)
        s += "\n"
        s += str(self.commands)
        return s

class InputFileDropTarget(wx.FileDropTarget):
    def __init__(self, callback):
        wx.FileDropTarget.__init__(self)
        self.callback = callback

    def OnDropFiles(self, x, y, filenames):
        self.callback(None, filenames)
        return True

class State(Enum):
    IDLE = 0
    RUNNING = 1
    INTERRUPTED = 2

class SpeechSpeedChangerGui(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title='', size=(400, 600))
        self.SetMinSize((400, 600))
        self.InitUi()
        self.in_list = []
        self.out_dir = ''
        self.audio_items = []
        self.processed_files = {}
        self.state = State.IDLE
        self.SetApplicationPath()
        self.Show()

    def SetApplicationPath(self):
        if getattr(sys, 'frozen', False):
            self.application_path = sys._MEIPASS
        else:
            self.application_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(self.application_path)

    def InitUi(self):
        panel = wx.Panel(self, wx.ID_ANY, style=wx.RAISED_BORDER)

        layout = wx.BoxSizer(wx.VERTICAL)
        listLayout = wx.StaticBoxSizer(wx.VERTICAL, panel, label="Input files")
        ioLayout = wx.StaticBoxSizer(wx.HORIZONTAL, panel, label="Output")
        outDirLayout = wx.StaticBoxSizer(wx.VERTICAL, panel, 'Output directory')
        presetLayout = wx.StaticBoxSizer(wx.HORIZONTAL, panel, 'Settings')

        self.inputTextCtrl = wx.TextCtrl(panel, wx.ID_ANY, size=(-1, 100), style=wx.TE_MULTILINE)
        self.text = wx.TextCtrl(panel, wx.ID_ANY, style=wx.TE_MULTILINE, size=(-1, 100))
        self.outDirPicker = wx.DirPickerCtrl(panel, size=(400, -1))
        self.outFormatComboBox = wx.ComboBox(panel, wx.ID_ANY, style=wx.CB_READONLY, size=(120, -1))

        self.progressGauge = wx.Gauge(panel, wx.ID_ANY, style=wx.GA_HORIZONTAL|wx.GA_PROGRESS)

        self.presetComboBox = wx.ComboBox(panel, wx.ID_ANY, style=wx.CB_READONLY, size=(110, -1))
        self.mergeCheck = wx.CheckBox(panel, wx.ID_ANY, label="Merge")
        self.startButton = wx.Button(panel, wx.ID_ANY, label="Start")

        dt = InputFileDropTarget(self.GenerateParams)
        self.inputTextCtrl.SetDropTarget(dt)

        self.LoadPresets()
        self.LoadOutFormat()

        self.mergeCheck.SetValue(True)

        listLayout.Add(self.inputTextCtrl, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5, proportion=1)

        ioLayout.Add(self.text, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, proportion=1, border=5)

        outDirLayout.Add(self.outDirPicker)

        presetLayout.Add(self.outFormatComboBox, flag=wx.EXPAND|wx.RIGHT, border=5)
        presetLayout.Add(self.presetComboBox, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        presetLayout.Add(self.mergeCheck, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)

        layout.Add(listLayout, flag=wx.EXPAND|wx.ALL, border=5, proportion=1)
        layout.Add(ioLayout, flag=wx.EXPAND|wx.ALL, proportion=1, border=5)
        layout.Add(outDirLayout, flag=wx.EXPAND|wx.LEFT|wx.RIGHT, border=5)
        layout.Add(presetLayout, flag=wx.EXPAND|wx.ALL, border=5)
        layout.Add(self.startButton, flag=wx.EXPAND|wx.ALL, border=5)
        layout.Add(self.progressGauge, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=10)

        self.Bind(wx.EVT_LISTBOX, self.GenerateParams, self.inputTextCtrl)
        self.Bind(wx.EVT_BUTTON, self.Convert, self.startButton)
        self.Bind(wx.EVT_COMBOBOX, self.GenerateParams, self.presetComboBox)
        self.Bind(wx.EVT_COMBOBOX, self.GenerateParams, self.outFormatComboBox)
        self.Bind(wx.EVT_DIRPICKER_CHANGED, self.GenerateParams, self.outDirPicker)

        panel.SetSizer(layout)

    def LoadPresets(self):
        self.presetComboBox.Append('2,3,4', {'speed':[2,3,4]})
        self.presetComboBox.Append('2,3,4,2', {'speed':[2,3,4,2]})
        self.presetComboBox.Append('1,2,3,4,1', {'speed':[1,2,3,4,1]})
        self.presetComboBox.Append('2,3,4,5', {'speed':[2,3,4,5]})
        self.presetComboBox.Append('2,3,4,5,2', {'speed':[2,3,4,5,2]})
        self.presetComboBox.Append('1,2,3,4,5,1', {'speed':[2,3,4,5,1]})
        self.presetComboBox.Append('2,3,4,5,6', {'speed':[2,3,4,5,6]})
        self.presetComboBox.Append('2,3,4,5,6,2', {'speed':[2,3,4,5,6,2]})
        self.presetComboBox.Append('1,2,3,4,5,6,1', {'speed':[1,2,3,4,5,6,1]})
        self.presetComboBox.Append('0.25', {'speed':[0.25]})
        self.presetComboBox.Append('0.5', {'speed':[0.5]})
        self.presetComboBox.Append('2', {'speed':[2]})
        self.presetComboBox.Append('3', {'speed':[3]})
        self.presetComboBox.Append('4', {'speed':[4]})
        self.presetComboBox.Append('5', {'speed':[5]})
        self.presetComboBox.Append('6', {'speed':[6]})
        self.presetComboBox.SetSelection(0)

    def LoadOutFormat(self):
        self.outFormatComboBox.Append('ALAC', {'cmd': './ffmpeg -y -acodec alac', 'ext': '.m4a'})
        self.outFormatComboBox.Append('FLAC', {'cmd': './ffmpeg -y -acodec flac', 'ext': '.flac'})
        self.outFormatComboBox.Append('AIFF', {'cmd': './ffmpeg -y -acodec pcm_s16be', 'ext': '.aiff'})
        self.outFormatComboBox.Append('WAV', {'cmd': './ffmpeg -y -acodec pcm_s16le', 'ext': '.wav'})
        self.outFormatComboBox.Append('MP3 (192kbps)', {'cmd': './ffmpeg -y -acodec libmp3lame -ab 192k', 'ext': '.mp3'})
        self.outFormatComboBox.Append('MP3 (160kbps)', {'cmd': './ffmpeg -y -acodec libmp3lame mp3 -ab 160k', 'ext': '.mp3'})
        self.outFormatComboBox.Append('MP3 (128kbps)', {'cmd': './ffmpeg -y -acodec libmp3lame mp3 -ab 128k', 'ext': '.mp3'})
        self.outFormatComboBox.Append('AAC (256kbps)', {'cmd': './ffmpeg -y -acodec aac -ab 128k -ar 44100', 'ext': '.m4a'})
        self.outFormatComboBox.Append('AAC (128kbps)', {'cmd': './ffmpeg -y -acodec aac -ab 256k -ar 44100', 'ext': '.m4a'})
        self.outFormatComboBox.SetSelection(0)

    def RunProcess(self, args):
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            ps = subprocess.Popen(args, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        else:
            ps = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        while True:
            line = ps.stdout.readline().decode()
            if line:
                self.text.write(line)
                wx.Yield()
            else:
                break

    def GetMetaData(self, in_file):
        args = ['./ffmpeg', '-y', '-i', in_file, '-f', 'ffmetadata', 'metadata.txt']
        self.RunProcess(args)

        metadata = ''
        with open('metadata.txt', 'r') as f:
            metadata = f.read()
        return metadata

    def Speedup(self, event, audio_item):
        in_file = audio_item.in_file

        if in_file.endswith('.wav'):
            shutil.copy(in_file, 'tmp.wav')
        else:
            args = ['./ffmpeg', '-i', in_file, 'tmp.wav', '-y']
            self.RunProcess(args)

        args = ['./ffmpeg', '-y', '-i', in_file, '-f', 'ffmetadata', 'metadata.txt']
        self.RunProcess(args)

        for i, speed in enumerate(audio_item.speed_list):
            args = ['./sonic', '-q', '-s', f"{speed:.2f}", 'tmp.wav', 'tmp2.wav']
            self.RunProcess(args)

            audio_item.commands[i][2] = 'tmp2.wav'
            audio_item.commands[i][3:3] = ['-i', 'metadata.txt', '-map_metadata', '1']
            self.RunProcess(audio_item.commands[i])

        try:
            os.remove('tmp.wav')
            os.remove('tmp2.wav')
        except:
            pass


    def GenerateParams(self, event, in_list=None):
        if in_list:
            if len(in_list) == 1:
                head, tail = os.path.split(in_list[0])
                self.inputTextCtrl.SetValue(tail)
            else:
                commonpath = os.path.commonpath(in_list)
                in_list_to_show = [name[len(commonpath)+1:] for name in in_list]
                self.inputTextCtrl.SetValue("\n".join(in_list_to_show))
            self.in_list = in_list

        if not self.in_list:
            return

        out_format = self.outFormatComboBox.GetClientData(self.outFormatComboBox.GetSelection())
        speed_list = self.presetComboBox.GetClientData(self.presetComboBox.GetSelection())['speed']

        head = self.outDirPicker.GetPath()
        if not head or not os.path.exists(head):
            head = os.path.abspath(os.path.expanduser('~'))
            self.out_dir= head
            self.outDirPicker.SetPath(head)
        self.out_dir= head

        self.audio_items = [AudioItem(item, speed_list, self.out_dir, out_format) for item in self.in_list]

        self.text.Clear()
        for out_files in [audio_item.out_files for audio_item in self.audio_items]:
            self.text.write(''.join([f"{os.path.split(out_file)[1]}\n" for out_file in out_files]))

    def LockUi(self, lock=True):
        if lock:
            self.inputTextCtrl.Disable()
            self.mergeCheck.Disable()
            self.outDirPicker.Disable() 
            self.progressGauge.Disable() 
            self.presetComboBox.Disable() 
            self.outFormatComboBox.Disable() 
        else:
            self.inputTextCtrl.Enable()
            self.mergeCheck.Enable()
            self.outDirPicker.Enable() 
            self.progressGauge.Enable() 
            self.presetComboBox.Enable() 
            self.outFormatComboBox.Enable() 

    def Convert(self, event):
        if self.state == State.RUNNING:
            self.state = State.INTERRUPTED
            self.LockUi(False)
            self.startButton.SetLabel("Start")
            return
        elif self.state == State.IDLE:
            self.state = State.RUNNING
            self.LockUi(True)
            self.startButton.SetLabel("Stop")
            self.text.Clear()


        self.GenerateParams(None)

        self.progressGauge.SetRange(len(self.audio_items) - 1)
        self.progressGauge.SetValue(0)

        self.processed_files = {} 
        for i, audio_item in enumerate(self.audio_items):
            if audio_item.in_file not in self.processed_files:
                self.Speedup(None, audio_item)
                self.processed_files[audio_item.in_file] = True
            self.progressGauge.SetValue(i)

            if self.state == State.INTERRUPTED:
                self.progressGauge.SetValue(0)
                self.state = State.IDLE
                self.LockUi(False)
                self.startButton.SetLabel("Start")
                return

        out_format = self.outFormatComboBox.GetClientData(self.outFormatComboBox.GetSelection())
        ext = out_format['ext']

        if self.mergeCheck.IsChecked():
            with open('./merge.txt', 'w') as f:
                for audio_item in self.audio_items:
                    for out_file in audio_item.out_files:
                        f.write(f"file '{out_file}'\n")
            
            args = ['./ffmpeg', '-y', '-i', self.audio_items[0].in_file, '-f', 'ffmetadata', 'metadata.txt']
            self.RunProcess(args)

            merged_name = "_".join([str(speed) for speed in self.audio_items[0].speed_list]) + ext
            merged_name = os.path.join(self.out_dir, merged_name)
            if ext == '.flac':
                args = ['./ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', 'merge.txt', '-i', 'metadata.txt', '-map_metadata', '1', merged_name]
                args = ['./ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', 'merge.txt', '-i', 'metadata.txt', '-map_metadata', '1', '-codec', 'copy', merged_name]
            else:
                args = ['./ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', 'merge.txt', '-i', 'metadata.txt', '-map_metadata', '1', '-codec', 'copy', merged_name]
            self.RunProcess(args)
            os.remove('./merge.txt')

            for audio_item in self.audio_items:
                for out_file in audio_item.out_files:
                    try:
                        os.remove(out_file)
                    except:
                        pass

        self.state = State.IDLE
        self.LockUi(False)
        self.startButton.SetLabel("Start")

if __name__ == '__main__':
    app = wx.App()
    SpeechSpeedChangerGui()
    app.MainLoop()

