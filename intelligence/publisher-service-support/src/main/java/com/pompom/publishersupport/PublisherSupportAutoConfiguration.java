package com.pompom.publishersupport;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.persistence.autoconfigure.EntityScan;
import org.springframework.context.annotation.Import;

/** Auto-registers support persistence when a publisher service consumes this library. */
@AutoConfiguration
@EntityScan(basePackageClasses = ProviderOperationRecord.class)
@Import(ProviderOperationRepository.class)
public class PublisherSupportAutoConfiguration {}
