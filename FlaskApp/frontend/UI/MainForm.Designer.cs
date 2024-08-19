namespace MonitoringUI
{
    partial class MainForm
    {
        private System.ComponentModel.IContainer components = null;
        private System.Windows.Forms.TextBox urlTextBox;
        private System.Windows.Forms.Button monitorButton;
        private System.Windows.Forms.Label urlLabel;
        private System.Windows.Forms.TextBox labelTextBox;
        private System.Windows.Forms.Button outlookButton;
        private System.Windows.Forms.Label labelLabel;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            this.urlTextBox = new System.Windows.Forms.TextBox();
            this.monitorButton = new System.Windows.Forms.Button();
            this.urlLabel = new System.Windows.Forms.Label();
            this.labelTextBox = new System.Windows.Forms.TextBox();
            this.outlookButton = new System.Windows.Forms.Button();
            this.labelLabel = new System.Windows.Forms.Label();
            this.SuspendLayout();
            // 
            // urlTextBox
            // 
            this.urlTextBox.Location = new System.Drawing.Point(100, 30);
            this.urlTextBox.Name = "urlTextBox";
            this.urlTextBox.Size = new System.Drawing.Size(200, 20);
            this.urlTextBox.TabIndex = 0;
            // 
            // monitorButton
            // 
            this.monitorButton.Location = new System.Drawing.Point(320, 28);
            this.monitorButton.Name = "monitorButton";
            this.monitorButton.Size = new System.Drawing.Size(100, 23);
            this.monitorButton.TabIndex = 1;
            this.monitorButton.Text = "Monitor URL";
            this.monitorButton.UseVisualStyleBackColor = true;
            this.monitorButton.Click += new System.EventHandler(this.monitorButton_Click);
            // 
            // urlLabel
            // 
            this.urlLabel.AutoSize = true;
            this.urlLabel.Location = new System.Drawing.Point(30, 33);
            this.urlLabel.Name = "urlLabel";
            this.urlLabel.Size = new System.Drawing.Size(64, 13);
            this.urlLabel.TabIndex = 2;
            this.urlLabel.Text = "Monitor URL:";
            // 
            // labelTextBox
            // 
            this.labelTextBox.Location = new System.Drawing.Point(100, 70);
            this.labelTextBox.Name = "labelTextBox";
            this.labelTextBox.Size = new System.Drawing.Size(200, 20);
            this.labelTextBox.TabIndex = 3;
            // 
            // outlookButton
            // 
            this.outlookButton.Location = new System.Drawing.Point(320, 68);
            this.outlookButton.Name = "outlookButton";
            this.outlookButton.Size = new System.Drawing.Size(100, 23);
            this.outlookButton.TabIndex = 4;
            this.outlookButton.Text = "Check Outlook";
            this.outlookButton.UseVisualStyleBackColor = true;
            this.outlookButton.Click += new System.EventHandler(this.outlookButton_Click);
            // 
            // labelLabel
            // 
            this.labelLabel.AutoSize = true;
            this.labelLabel.Location = new System.Drawing.Point(30, 73);
            this.labelLabel.Name = "labelLabel";
            this.labelLabel.Size = new System.Drawing.Size(60, 13);
            this.labelLabel.TabIndex = 5;
            this.labelLabel.Text = "Search Label:";
            // 
            // MainForm
            // 
            this.ClientSize = new System.Drawing.Size(450, 120);
            this.Controls.Add(this.labelLabel);
            this.Controls.Add(this.outlookButton);
            this.Controls.Add(this.labelTextBox);
            this.Controls.Add(this.urlLabel);
            this.Controls.Add(this.monitorButton);
            this.Controls.Add(this.urlTextBox);
            this.Name = "MainForm";
            this.Text = "Monitoring Application";
            this.ResumeLayout(false);
            this.PerformLayout();
        }
    }
}
