package com.pompom.creative.notification;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.metrics.VideoMetrics;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.math.BigDecimal;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.MailException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

/**
 * Email notification service for key system events.
 *
 * <p>Sends notifications for: - Render completion (success/failure) - Publication success/failure -
 * Performance alerts (viral videos, underperforming content) - Budget warnings (credit threshold
 * reached)
 *
 * <p>Uses Spring's JavaMailSender with async execution to avoid blocking.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class EmailNotificationService {

  private final JavaMailSender mailSender;

  @Value("${pompom.notifications.email.from:noreply@pompomhills.com}")
  private String fromEmail;

  @Value("${pompom.notifications.email.to:admin@pompomhills.com}")
  private String toEmail;

  @Value("${pompom.notifications.email.enabled:false}")
  private boolean emailEnabled;

  /** Send render completion notification. */
  @Async
  public void sendRenderCompletionEmail(RenderJob job) {
    if (!emailEnabled) {
      log.debug("Email notifications disabled, skipping render completion email");
      return;
    }

    log.info("Sending render completion email: jobId={}, status={}", job.getId(), job.getStatus());

    String subject = String.format("Render Job %s - %s", job.getId(), job.getStatus());

    String body = buildRenderCompletionBody(job);

    sendHtmlEmail(toEmail, subject, body);
  }

  /** Send publication success notification. */
  @Async
  public void sendPublicationSuccessEmail(PublicationJob job) {
    if (!emailEnabled) {
      return;
    }

    log.info(
        "Sending publication success email: jobId={}, platform={}", job.getId(), job.getPlatform());

    String subject = String.format("Publication Success - %s", job.getPlatform());
    String body = buildPublicationSuccessBody(job);

    sendHtmlEmail(toEmail, subject, body);
  }

  /** Send publication failure notification. */
  @Async
  public void sendPublicationFailureEmail(PublicationJob job) {
    if (!emailEnabled) {
      return;
    }

    log.info(
        "Sending publication failure email: jobId={}, platform={}", job.getId(), job.getPlatform());

    String subject = String.format("Publication FAILED - %s", job.getPlatform());
    String body = buildPublicationFailureBody(job);

    sendHtmlEmail(toEmail, subject, body);
  }

  /** Send performance alert for viral video. */
  @Async
  public void sendViralVideoAlert(PublicationJob job, VideoMetrics metrics) {
    if (!emailEnabled) {
      return;
    }

    log.info("Sending viral video alert: jobId={}, views={}", job.getId(), metrics.getViews());

    String subject = String.format("🔥 Viral Alert - %s", job.getPlatform());
    String body = buildViralAlertBody(job, metrics);

    sendHtmlEmail(toEmail, subject, body);
  }

  /** Send budget warning notification. */
  @Async
  public void sendBudgetWarningEmail(BigDecimal remainingCredits, BigDecimal monthlyBudget) {
    if (!emailEnabled) {
      return;
    }

    log.info(
        "Sending budget warning email: remaining={}, budget={}", remainingCredits, monthlyBudget);

    String subject = "⚠️ Budget Warning - OpenArt Credits Low";
    String body = buildBudgetWarningBody(remainingCredits, monthlyBudget);

    sendHtmlEmail(toEmail, subject, body);
  }

  /** Send simple text email. */
  private void sendSimpleEmail(String to, String subject, String text) {
    try {
      SimpleMailMessage message = new SimpleMailMessage();
      message.setFrom(fromEmail);
      message.setTo(to);
      message.setSubject(subject);
      message.setText(text);

      mailSender.send(message);
      log.info("Email sent successfully: to={}, subject={}", to, subject);
    } catch (MailException e) {
      log.error("Failed to send email: to={}, subject={}", to, subject, e);
    }
  }

  /** Send HTML email. */
  private void sendHtmlEmail(String to, String subject, String htmlBody) {
    try {
      MimeMessage message = mailSender.createMimeMessage();
      MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");

      helper.setFrom(fromEmail);
      helper.setTo(to);
      helper.setSubject(subject);
      helper.setText(htmlBody, true); // true = HTML

      mailSender.send(message);
      log.info("HTML email sent successfully: to={}, subject={}", to, subject);
    } catch (MessagingException | MailException e) {
      log.error("Failed to send HTML email: to={}, subject={}", to, subject, e);
    }
  }

  /** Build render completion email body. */
  private String buildRenderCompletionBody(RenderJob job) {
    return String.format(
        """
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Render Job %s</h2>
                <p><strong>Status:</strong> %s</p>
                <p><strong>Job Type:</strong> %s</p>
                <p><strong>Content ID:</strong> %s</p>
                <p><strong>Prompt Version:</strong> %s</p>
                <p><strong>Credits Used:</strong> %s</p>
                <p><strong>Started:</strong> %s</p>
                <p><strong>Completed:</strong> %s</p>
                %s
                <hr>
                <p style="color: #666; font-size: 12px;">Pompom Creative Intelligence System</p>
            </body>
            </html>
            """,
        job.getStatus().equals(RenderJob.RenderJobStatus.COMPLETE) ? "Completed ✅" : "Failed ❌",
        job.getStatus(),
        job.getJobType(),
        job.getContentId(),
        job.getPromptVersionId(),
        job.getCreditsActual() != null ? job.getCreditsActual() : "N/A",
        job.getStartedAt(),
        job.getCompletedAt() != null ? job.getCompletedAt() : job.getFailedAt(),
        job.getErrorMessage() != null
            ? String.format(
                "<p style=\"color: red;\"><strong>Error:</strong> %s</p>", job.getErrorMessage())
            : "");
  }

  /** Build publication success email body. */
  private String buildPublicationSuccessBody(PublicationJob job) {
    return String.format(
        """
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Publication Success ✅</h2>
                <p><strong>Platform:</strong> %s</p>
                <p><strong>Video ID:</strong> %s</p>
                <p><strong>Post URL:</strong> <a href="%s">%s</a></p>
                <p><strong>Published at:</strong> %s</p>
                <hr>
                <p style="color: #666; font-size: 12px;">Pompom Creative Intelligence System</p>
            </body>
            </html>
            """,
        job.getPlatform(),
        job.getPlatformPostId(),
        job.getPostUrl(),
        job.getPostUrl(),
        job.getCompletedAt());
  }

  /** Build publication failure email body. */
  private String buildPublicationFailureBody(PublicationJob job) {
    return String.format(
        """
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Publication FAILED ❌</h2>
                <p><strong>Platform:</strong> %s</p>
                <p><strong>Error:</strong> %s</p>
                <p><strong>Failed at:</strong> %s</p>
                <hr>
                <p style="color: #666; font-size: 12px;">Pompom Creative Intelligence System</p>
            </body>
            </html>
            """,
        job.getPlatform(),
        job.getErrorMessage(),
        job.getCompletedAt() != null ? job.getCompletedAt() : "Not completed");
  }

  /** Build viral video alert body. */
  private String buildViralAlertBody(PublicationJob job, VideoMetrics metrics) {
    return String.format(
        """
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>🔥 Viral Video Alert!</h2>
                <p>Your video is performing exceptionally well!</p>
                <p><strong>Platform:</strong> %s</p>
                <p><strong>Post URL:</strong> <a href="%s">%s</a></p>
                <h3>Metrics:</h3>
                <ul>
                    <li><strong>Views:</strong> %,d</li>
                    <li><strong>Likes:</strong> %,d</li>
                    <li><strong>Comments:</strong> %,d</li>
                    <li><strong>Shares:</strong> %,d</li>
                    <li><strong>Engagement Rate:</strong> %.2f%%</li>
                    <li><strong>Virality Score:</strong> %.2f</li>
                </ul>
                <hr>
                <p style="color: #666; font-size: 12px;">Pompom Creative Intelligence System</p>
            </body>
            </html>
            """,
        job.getPlatform(),
        job.getPostUrl(),
        job.getPostUrl(),
        metrics.getViews(),
        metrics.getLikes(),
        metrics.getComments(),
        metrics.getShares(),
        metrics.calculateEngagementRate(),
        metrics.calculateViralityScore());
  }

  /** Build budget warning email body. */
  private String buildBudgetWarningBody(BigDecimal remainingCredits, BigDecimal monthlyBudget) {
    BigDecimal percentRemaining =
        remainingCredits
            .divide(monthlyBudget, 4, java.math.RoundingMode.HALF_UP)
            .multiply(BigDecimal.valueOf(100));

    return String.format(
        """
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>⚠️ Budget Warning</h2>
                <p>Your OpenArt credit balance is running low.</p>
                <p><strong>Remaining Credits:</strong> %s</p>
                <p><strong>Monthly Budget:</strong> %s</p>
                <p><strong>Percentage Remaining:</strong> %.1f%%</p>
                <p>Please consider topping up your credits to avoid service interruption.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">Pompom Creative Intelligence System</p>
            </body>
            </html>
            """,
        remainingCredits, monthlyBudget, percentRemaining);
  }
}
