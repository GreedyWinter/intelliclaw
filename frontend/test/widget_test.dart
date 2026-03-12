import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart';

void main() {
  testWidgets('Intelliclaw app loads', (WidgetTester tester) async {
    await tester.pumpWidget(const IntelliclawApp());

    expect(find.text('Intelliclaw'), findsOneWidget);
    expect(find.text('Test Backend'), findsOneWidget);
  });
}