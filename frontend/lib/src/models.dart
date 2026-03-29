class Project {
  const Project({
    required this.id,
    required this.name,
    required this.createdAt,
    required this.documentCount,
  });

  final int id;
  final String name;
  final String createdAt;
  final int documentCount;

  factory Project.fromJson(Map<String, dynamic> json) {
    return Project(
      id: json['id'] as int,
      name: json['name'] as String,
      createdAt: json['created_at'] as String? ?? '',
      documentCount: json['document_count'] as int? ?? 0,
    );
  }
}

class ProjectSummary {
  const ProjectSummary({
    required this.projectCount,
    required this.documentCount,
  });

  final int projectCount;
  final int documentCount;

  factory ProjectSummary.fromJson(Map<String, dynamic> json) {
    return ProjectSummary(
      projectCount: json['project_count'] as int? ?? 0,
      documentCount: json['document_count'] as int? ?? 0,
    );
  }
}

class ProjectDocument {
  const ProjectDocument({
    required this.id,
    required this.projectId,
    required this.filename,
    required this.filePath,
    required this.contentType,
    required this.sizeBytes,
    required this.status,
    required this.createdAt,
  });

  final int id;
  final int projectId;
  final String filename;
  final String? filePath;
  final String? contentType;
  final int? sizeBytes;
  final String status;
  final String createdAt;

  factory ProjectDocument.fromJson(Map<String, dynamic> json) {
    return ProjectDocument(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      filename: json['filename'] as String,
      filePath: json['file_path'] as String?,
      contentType: json['content_type'] as String?,
      sizeBytes: json['size_bytes'] as int?,
      status: json['status'] as String? ?? 'uploaded',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class AnalysisRun {
  const AnalysisRun({
    required this.id,
    required this.projectId,
    required this.status,
    required this.pipelineVersion,
    required this.stage,
    required this.humanReviewStatus,
    required this.currentIteration,
    required this.summary,
    required this.resultPath,
    required this.errorMessage,
    required this.tracePath,
    required this.summaryPath,
    required this.failureDetails,
    required this.tracePreview,
    required this.latestTraceMessage,
    required this.gapSummaryPath,
    required this.gapSummaryContent,
    required this.reviewArtifacts,
    required this.stepResults,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final int projectId;
  final String status;
  final String pipelineVersion;
  final String stage;
  final String humanReviewStatus;
  final int currentIteration;
  final String? summary;
  final String? resultPath;
  final String? errorMessage;
  final String? tracePath;
  final String? summaryPath;
  final Map<String, dynamic> failureDetails;
  final List<TraceEntry> tracePreview;
  final String? latestTraceMessage;
  final String? gapSummaryPath;
  final String? gapSummaryContent;
  final List<ReviewArtifact> reviewArtifacts;
  final List<AnalysisStep> stepResults;
  final String createdAt;
  final String updatedAt;

  factory AnalysisRun.fromJson(Map<String, dynamic> json) {
    final steps = (json['step_results'] as List<dynamic>? ?? const [])
        .map((item) => AnalysisStep.fromJson(item as Map<String, dynamic>))
        .toList();

    return AnalysisRun(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      status: json['status'] as String? ?? 'pending',
      pipelineVersion: json['pipeline_version'] as String? ?? 'v1',
      stage: json['stage'] as String? ?? 'extraction',
      humanReviewStatus: json['human_review_status'] as String? ?? 'not_requested',
      currentIteration: json['current_iteration'] as int? ?? 1,
      summary: json['summary'] as String?,
      resultPath: json['result_path'] as String?,
      errorMessage: json['error_message'] as String?,
      tracePath: json['trace_path'] as String?,
      summaryPath: json['summary_path'] as String?,
      failureDetails: Map<String, dynamic>.from(
        json['failure_details'] as Map<String, dynamic>? ?? const {},
      ),
      tracePreview: (json['trace_preview'] as List<dynamic>? ?? const [])
          .map((item) => TraceEntry.fromJson(item as Map<String, dynamic>))
          .toList(),
      latestTraceMessage: json['latest_trace_message'] as String?,
      gapSummaryPath: json['gap_summary_path'] as String?,
      gapSummaryContent: json['gap_summary_content'] as String?,
      reviewArtifacts: (json['review_artifacts'] as List<dynamic>? ?? const [])
          .map((item) => ReviewArtifact.fromJson(item as Map<String, dynamic>))
          .toList(),
      stepResults: steps,
      createdAt: json['created_at'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
    );
  }
}

class TraceEntry {
  const TraceEntry({
    required this.timestamp,
    required this.source,
    required this.target,
    required this.eventType,
    required this.message,
    required this.documentId,
    required this.attempt,
    required this.payload,
  });

  final String timestamp;
  final String? source;
  final String? target;
  final String eventType;
  final String message;
  final int? documentId;
  final int? attempt;
  final Map<String, dynamic> payload;

  factory TraceEntry.fromJson(Map<String, dynamic> json) {
    return TraceEntry(
      timestamp: json['timestamp'] as String? ?? '',
      source: json['source'] as String?,
      target: json['target'] as String?,
      eventType: json['event_type'] as String? ?? '',
      message: json['message'] as String? ?? '',
      documentId: json['document_id'] as int?,
      attempt: json['attempt'] as int?,
      payload: Map<String, dynamic>.from(
        json['payload'] as Map<String, dynamic>? ?? const {},
      ),
    );
  }
}

class AnalysisStep {
  const AnalysisStep({
    required this.name,
    required this.status,
    required this.documentId,
    required this.attempt,
    required this.details,
  });

  final String name;
  final String status;
  final int? documentId;
  final int? attempt;
  final Map<String, dynamic> details;

  factory AnalysisStep.fromJson(Map<String, dynamic> json) {
    return AnalysisStep(
      name: json['name'] as String? ?? '',
      status: json['status'] as String? ?? '',
      documentId: json['document_id'] as int?,
      attempt: json['attempt'] as int?,
      details: (json['details'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

class ReviewArtifact {
  const ReviewArtifact({
    required this.documentId,
    required this.filename,
    required this.csvPath,
    required this.previewRows,
    required this.evaluatorFeedback,
    required this.humanFeedback,
    required this.approved,
  });

  final int documentId;
  final String filename;
  final String csvPath;
  final List<Map<String, dynamic>> previewRows;
  final List<String> evaluatorFeedback;
  final List<String> humanFeedback;
  final bool approved;

  factory ReviewArtifact.fromJson(Map<String, dynamic> json) {
    return ReviewArtifact(
      documentId: json['document_id'] as int,
      filename: json['filename'] as String? ?? '',
      csvPath: json['csv_path'] as String? ?? '',
      previewRows: (json['preview_rows'] as List<dynamic>? ?? const [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(),
      evaluatorFeedback: (json['evaluator_feedback'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      humanFeedback: (json['human_feedback'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      approved: json['approved'] as bool? ?? false,
    );
  }
}

class ProjectDetail {
  const ProjectDetail({
    required this.project,
    required this.documents,
    required this.analysisRuns,
  });

  final Project project;
  final List<ProjectDocument> documents;
  final List<AnalysisRun> analysisRuns;

  factory ProjectDetail.fromJson(Map<String, dynamic> json) {
    return ProjectDetail(
      project: Project.fromJson(json),
      documents: (json['documents'] as List<dynamic>? ?? const [])
          .map((item) => ProjectDocument.fromJson(item as Map<String, dynamic>))
          .toList(),
      analysisRuns: (json['analysis_runs'] as List<dynamic>? ?? const [])
          .map((item) => AnalysisRun.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}
