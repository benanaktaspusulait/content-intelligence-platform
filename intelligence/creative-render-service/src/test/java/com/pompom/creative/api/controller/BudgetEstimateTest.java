package com.pompom.creative.api.controller;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.service.CreditTrackingService;
import com.pompom.creative.service.BudgetAlertService;

class BudgetEstimateTest {
  @Test void exposesExistingReservationEstimateHonestlyWithoutProviderDispatch() {
    var credits=mock(CreditTrackingService.class);
    when(credits.getEstimatedCost(RenderJob.JobType.VIDEO)).thenReturn(new BigDecimal("15"));
    when(credits.getRemainingCredits()).thenReturn(new BigDecimal("1000"));
    var controller=new BudgetController(credits,mock(BudgetAlertService.class));
    assertThat(controller.renderEstimate()).containsEntry("providerCallPerformed",false)
        .containsEntry("basis","CONFIGURED_VIDEO_BUDGET_ESTIMATE_NOT_PROVIDER_QUOTE")
        .containsEntry("estimatedCredits",new BigDecimal("15"));
    verify(credits).getEstimatedCost(RenderJob.JobType.VIDEO);verify(credits).getRemainingCredits();verifyNoMoreInteractions(credits);
  }
}
