import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart';
import 'package:frontend/src/api/intelliclaw_api.dart';
import 'package:frontend/src/models.dart';

class FakeIntelliclawApi extends IntelliclawApi {
  @override
  Future<bool> healthCheck() async => true;

  @override
  Future<ProjectSummary> fetchSummary() async {
    return const ProjectSummary(projectCount: 1, documentCount: 2);
  }

  @override
  Future<List<Project>> fetchProjects() async {
    return const [
      Project(
        id: 1,
        name: 'Demo project',
        createdAt: '2026-03-14T00:00:00',
        documentCount: 2,
      ),
    ];
  }
}

void main() {
  testWidgets('Intelliclaw app loads', (WidgetTester tester) async {
    await tester.pumpWidget(IntelliclawApp(api: FakeIntelliclawApi()));
    await tester.pumpAndSettle();

    expect(find.text('Intelliclaw'), findsOneWidget);
    expect(find.text('Create research project'), findsOneWidget);
    expect(find.text('Demo project'), findsOneWidget);
  });
}
