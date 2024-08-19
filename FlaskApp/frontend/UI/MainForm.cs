using System;
using System.Windows.Forms;
using System.Net.Http;
using System.Net.Http.Json;

namespace MonitoringUI
{
    public partial class MainForm : Form
    {
        private static readonly HttpClient client = new HttpClient();

        public MainForm()
        {
            InitializeComponent();
        }

        private async void monitorButton_Click(object sender, EventArgs e)
        {
            var url = urlTextBox.Text;
            var response = await client.PostAsJsonAsync("http://localhost:5000/monitor", new { url });
            var result = await response.Content.ReadAsStringAsync();
            MessageBox.Show(result);
        }

        private async void outlookButton_Click(object sender, EventArgs e)
        {
            var label = labelTextBox.Text;
            var response = await client.PostAsJsonAsync("http://localhost:5000/outlook_check", new { label });
            var result = await response.Content.ReadAsStringAsync();
            MessageBox.Show(result);
        }
    }
}
