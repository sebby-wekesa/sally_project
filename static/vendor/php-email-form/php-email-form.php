<?php

class PHP_Email_Form
{
    public $to;
    public $from_name;
    public $from_email;
    public $subject;
    public $message;
    public $headers;
    public $smtp;

    public $ajax = false;

    public function __construct()
    {
        $this->headers = "MIME-Version: 1.0" . "\r\n";
        $this->headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
    }

    public function add_message($content, $label, $label_length = 0)
    {
        $content = wordwrap($content, 70);
        $this->message .= "<p><strong>{$label}:</strong> {$content}</p>";
    }

    public function send()
    {
        $this->message .= "<p><strong>IP Address:</strong> {$_SERVER['REMOTE_ADDR']}</p>";

        if ($this->ajax) {
            $response = $this->mail_via_ajax();
            return $response;
        } else {
            return mail($this->to, $this->subject, $this->message, $this->headers);
        }
    }

    private function mail_via_ajax()
    {
        if (empty($this->to) || empty($this->from_name) || empty($this->from_email) || empty($this->subject) || empty($this->message)) {
            return 'Please fill in all required fields.';
        }

        if (!filter_var($this->from_email, FILTER_VALIDATE_EMAIL)) {
            return 'Invalid email address';
        }

        // Additional validation or security measures can be added here

        // Example using mail() function
        $success = mail($this->to, $this->subject, $this->message, $this->headers);

        if ($success) {
            return 'Email sent successfully!';
        } else {
            return 'Error sending email. Please try again later.';
        }
    }
}

?>

