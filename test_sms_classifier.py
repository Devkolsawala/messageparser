import pandas as pd
import re
import numpy as np
from typing import List, Tuple, Dict
import json
import random
from datetime import datetime

class CSVBasedTester:
    def __init__(self, classifier):
        self.classifier = classifier
        
        # Define pattern-based detection for ground truth labeling
        self.ground_truth_patterns = {
            "otp_indicators": [
                r'\b\d{4,8}\s*is\s*(?:your|the)\s*(?:otp|one\s*time\s*password)\b',
                r'\byour\s*(?:otp|one\s*time\s*password)\s*(?:is|:)\s*\d{4,8}\b',
                r'\botp\s*(?:is|:)\s*\d{4,8}\b',
                r'\bone\s*time\s*password\s*(?:is|:)\s*\d{4,8}\b',
                r'\buse\s*(?:otp|one\s*time\s*password)\s*\d{4,8}\b',
                r'\bto\s*(?:login|register|proceed).*(?:otp|one\s*time\s*password)\s*\d{4,8}\b',
                r'\b\d{4,8}.*is\s*your\s*(?:otp|one\s*time\s*password)\s*to\s*(?:login|register|proceed)\b',
            ],
            
            "banking_indicators": [
                r'\b(?:credited|debited)\s*by\s*rs\.?\s*[\d,]+',
                r'\btotal\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
                r'\bavailable\s*bal(?:ance)?\s*:\s*rs\.?\s*[\d,]+',
                r'\ba/c\s*\w+.*(?:credited|debited)',
                r'\baccount.*(?:credited|debited|balance)',
                r'\btransaction\s*(?:id|alert|reference)',
            ],
            
            "promotional_indicators": [
                r'\b\d+%\s*(?:daily\s*)?data\s*quota\s*used\b',
                r'\bwebinar\s*:',
                r'\bregister\s*now\s*:',
                r'\btap\s*to\s*reset\s*.*password',
                r'\bclick\s*(?:here|link)',
                r'\bvisit\s*:\s*https?://',
                r'\bdownload\s*.*app',
                r'\bspecial\s*(?:offer|discount)',
                r'\bcongratulations.*won',
                r'\brecharge\s*now',
            ],
            
            "government_indicators": [
                r'\b(?:aadhaar|aadhar|uid|pan|passport|voter|epic|kyc)\b',
                r'\bdriving\s*licen[cs]e\b',
                r'\bidentity\s*(?:verification|proof)\b',
                r'\bgovernment\s*service',
                r'\bgov\.in\b',
                r'\brto\b',
            ]
        }
        
        # Compile patterns
        self.compiled_patterns = {}
        for category, patterns in self.ground_truth_patterns.items():
            self.compiled_patterns[category] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def determine_ground_truth(self, message: str) -> str:
        """Determine the ground truth classification based on message content"""
        message_lower = message.lower()
        
        # Check for strong banking context first
        banking_score = sum(1 for pattern in self.compiled_patterns["banking_indicators"] 
                          if pattern.search(message))
        
        # Check for promotional content
        promo_score = sum(1 for pattern in self.compiled_patterns["promotional_indicators"] 
                         if pattern.search(message))
        
        # Check for OTP patterns
        otp_score = sum(1 for pattern in self.compiled_patterns["otp_indicators"] 
                       if pattern.search(message))
        
        # Check for government patterns
        gov_score = sum(1 for pattern in self.compiled_patterns["government_indicators"] 
                       if pattern.search(message))
        
        # Check for actual OTP number
        has_otp_number = bool(re.search(r'\b\d{4,8}\b', message))
        
        # Classification logic for ground truth
        # 1. If it has clear OTP patterns AND a number, it's likely an OTP
        if otp_score >= 1 and has_otp_number:
            # But check if it's a banking transaction with OTP mention
            if banking_score >= 2:  # Strong banking context
                return "Unknown"
            return "Security & Authentication - OTP verification"
        
        # 2. If it has strong banking indicators, it's banking/transaction
        if banking_score >= 2:
            return "Unknown"
        
        # 3. If it has strong promotional indicators, it's promotional
        if promo_score >= 2:
            return "Unknown"
        
        # 4. If it has government indicators but no OTP context, it's government
        if gov_score >= 1 and otp_score == 0:
            return "Government & Public Services - Identity services"
        
        # 5. If it has government + OTP, it's an OTP for government service
        if gov_score >= 1 and otp_score >= 1 and has_otp_number:
            return "Security & Authentication - OTP verification"
        
        # Default
        return "Unknown"

    def sample_messages_by_category(self, df: pd.DataFrame, n_per_category: int = 50) -> Dict[str, pd.DataFrame]:
        """Sample messages from CSV and categorize them for testing"""
        
        print(f"Sampling {n_per_category} messages per category from CSV...")
        
        # First, determine ground truth for all messages (sample a subset for efficiency)
        sample_size = min(10000, len(df))  # Sample max 10k for ground truth analysis
        df_sample = df.sample(n=sample_size, random_state=42)
        
        print(f"Analyzing {len(df_sample)} messages to determine ground truth categories...")
        
        # Add ground truth classification
        df_sample = df_sample.copy()
        df_sample['ground_truth'] = df_sample['message'].apply(self.determine_ground_truth)
        
        # Group by ground truth category
        categorized_samples = {}
        
        for category in df_sample['ground_truth'].unique():
            category_df = df_sample[df_sample['ground_truth'] == category]
            
            if len(category_df) > 0:
                # Sample up to n_per_category messages from this category
                sample_count = min(n_per_category, len(category_df))
                sampled = category_df.sample(n=sample_count, random_state=42)
                categorized_samples[category] = sampled
                
                print(f"Category '{category}': {sample_count} samples")
        
        return categorized_samples

    def test_sampled_messages(self, categorized_samples: Dict[str, pd.DataFrame]) -> Dict:
        """Test classifier accuracy on sampled messages"""
        
        results = {
            "category_results": {},
            "overall_metrics": {},
            "detailed_failures": [],
            "sample_stats": {}
        }
        
        print("\nTesting Classifier on Sampled CSV Data:")
        print("=" * 50)
        
        total_correct = 0
        total_messages = 0
        
        for ground_truth_category, sample_df in categorized_samples.items():
            print(f"\nTesting Category: {ground_truth_category}")
            print("-" * 40)
            
            correct = 0
            failures = []
            
            for _, row in sample_df.iterrows():
                message = str(row['message'])
                sender = str(row['sender_name']) if 'sender_name' in row and pd.notna(row['sender_name']) else ""
                
                # Get classifier prediction
                predicted = self.classifier.classify_message(message, sender)
                
                # Check if correct
                is_correct = predicted == ground_truth_category
                
                if is_correct:
                    correct += 1
                else:
                    failures.append({
                        "message": message,
                        "expected": ground_truth_category,
                        "predicted": predicted,
                        "sender": sender
                    })
            
            # Calculate accuracy for this category
            total_in_category = len(sample_df)
            accuracy = (correct / total_in_category) * 100 if total_in_category > 0 else 0
            
            results["category_results"][ground_truth_category] = {
                "correct": correct,
                "total": total_in_category,
                "accuracy": accuracy,
                "failures": failures
            }
            
            total_correct += correct
            total_messages += total_in_category
            
            print(f"Accuracy: {correct}/{total_in_category} ({accuracy:.1f}%)")
            
            # Show sample failures
            if failures and len(failures) <= 3:
                print("Sample failures:")
                for i, failure in enumerate(failures[:3], 1):
                    print(f"  {i}. Expected: {failure['expected']}")
                    print(f"     Predicted: {failure['predicted']}")
                    print(f"     Message: {failure['message'][:80]}...")
        
        # Calculate overall metrics
        overall_accuracy = (total_correct / total_messages) * 100 if total_messages > 0 else 0
        results["overall_metrics"] = {
            "total_correct": total_correct,
            "total_messages": total_messages,
            "overall_accuracy": overall_accuracy
        }
        
        # Summary
        print("\n" + "=" * 50)
        print("OVERALL TEST RESULTS")
        print("=" * 50)
        print(f"Total Messages Tested: {total_messages}")
        print(f"Correctly Classified: {total_correct}")
        print(f"Overall Accuracy: {overall_accuracy:.1f}%")
        
        return results

    def manual_verification_test(self, df: pd.DataFrame, n_samples: int = 20):
        """Sample random messages for manual verification by user"""
        
        print(f"\nManual Verification Test - {n_samples} Random Messages")
        print("=" * 60)
        print("You'll see random messages and their classifications.")
        print("Mark each as correct (c) or incorrect (i) to calculate accuracy.")
        
        # Sample random messages
        sample_df = df.sample(n=n_samples, random_state=np.random.randint(0, 10000))
        
        correct_count = 0
        total_count = 0
        
        for idx, (_, row) in enumerate(sample_df.iterrows(), 1):
            message = str(row['message'])
            sender = str(row['sender_name']) if 'sender_name' in row and pd.notna(row['sender_name']) else "Unknown"
            
            # Get classification
            classification = self.classifier.classify_message(message, sender)
            
            print(f"\nMessage {idx}/{n_samples}:")
            print("-" * 40)
            print(f"Sender: {sender}")
            print(f"Message: {message}")
            print(f"Classification: {classification}")
            
            # Ask user for verification
            while True:
                user_input = input("\nIs this classification correct? (c)orrect / (i)ncorrect / (s)kip / (d)debug / (q)uit: ").lower().strip()
                
                if user_input == 'c':
                    correct_count += 1
                    total_count += 1
                    print("Marked as CORRECT")
                    break
                elif user_input == 'i':
                    total_count += 1
                    print("Marked as INCORRECT")
                    correct_classification = input("What should the correct classification be?: ").strip()
                    print(f"User says it should be: {correct_classification}")
                    break
                elif user_input == 's':
                    print("Skipped")
                    break
                elif user_input == 'd':
                    print("\nDEBUG ANALYSIS:")
                    self.classifier.debug_classification(message, sender)
                    continue
                elif user_input == 'q':
                    print("Test terminated by user")
                    if total_count > 0:
                        accuracy = (correct_count / total_count) * 100
                        print(f"Accuracy so far: {correct_count}/{total_count} ({accuracy:.1f}%)")
                    return correct_count, total_count
                else:
                    print("Invalid input. Please enter 'c', 'i', 's', 'd', or 'q'")
        
        if total_count > 0:
            accuracy = (correct_count / total_count) * 100
            print(f"\nManual Verification Results:")
            print(f"Correct: {correct_count}/{total_count} ({accuracy:.1f}%)")
        else:
            print("No messages were manually verified.")
        
        return correct_count, total_count

    def pattern_based_accuracy_test(self, df: pd.DataFrame, n_samples: int = 200):
        """Test accuracy using pattern-based ground truth on sampled data"""
        
        print(f"\nPattern-Based Accuracy Test - {n_samples} Random Samples")
        print("=" * 60)
        
        # Sample random messages
        if len(df) < n_samples:
            sample_df = df.copy()
            print(f"Note: Dataset has only {len(df)} messages, using all.")
        else:
            sample_df = df.sample(n=n_samples, random_state=42)
        
        print(f"Testing {len(sample_df)} messages...")
        
        # Add ground truth and predictions
        sample_df = sample_df.copy()
        sample_df['ground_truth'] = sample_df['message'].apply(self.determine_ground_truth)
        
        # Get classifier predictions
        predictions = []
        for _, row in sample_df.iterrows():
            message = str(row['message'])
            sender = str(row['sender_name']) if 'sender_name' in row and pd.notna(row['sender_name']) else ""
            prediction = self.classifier.classify_message(message, sender)
            predictions.append(prediction)
        
        sample_df['predicted'] = predictions
        
        # Calculate accuracy metrics
        results = self._calculate_accuracy_metrics(sample_df)
        
        # Print results
        self._print_accuracy_results(results, sample_df)
        
        return results, sample_df

    def targeted_category_test(self, df: pd.DataFrame, n_per_category: int = 30):
        """Test specific categories by finding messages that likely belong to each category"""
        
        print(f"\nTargeted Category Test - {n_per_category} samples per category")
        print("=" * 60)
        
        category_filters = {
            "Likely OTP": [
                lambda x: 'otp' in x.lower() and bool(re.search(r'\b\d{4,8}\b', x)),
                lambda x: 'one time password' in x.lower() and bool(re.search(r'\b\d{4,8}\b', x)),
                lambda x: bool(re.search(r'\b\d{4,8}\s*is\s*(?:your|the)\s*otp', x, re.IGNORECASE)),
            ],
            
            "Likely Banking": [
                lambda x: 'credited' in x.lower() and 'rs.' in x.lower(),
                lambda x: 'debited' in x.lower() and 'rs.' in x.lower(),
                lambda x: 'balance' in x.lower() and 'rs.' in x.lower(),
                lambda x: 'a/c' in x.lower() and ('credited' in x.lower() or 'debited' in x.lower()),
            ],
            
            "Likely Promotional": [
                lambda x: 'webinar' in x.lower(),
                lambda x: 'data quota' in x.lower(),
                lambda x: 'click' in x.lower() and 'http' in x.lower(),
                lambda x: 'register now' in x.lower(),
                lambda x: 'tap to reset' in x.lower(),
            ],
            
            "Likely Government": [
                lambda x: 'aadhaar' in x.lower() and 'otp' not in x.lower(),
                lambda x: 'pan card' in x.lower(),
                lambda x: 'kyc' in x.lower() and not bool(re.search(r'\b\d{4,8}\b', x)),
                lambda x: 'passport' in x.lower(),
                lambda x: 'voter id' in x.lower(),
            ]
        }
        
        results = {}
        
        for category, filters in category_filters.items():
            print(f"\nTesting {category}:")
            print("-" * 30)
            
            # Find messages matching any of the filters
            matching_messages = []
            
            for _, row in df.iterrows():
                message = str(row['message'])
                if any(filter_func(message) for filter_func in filters):
                    matching_messages.append(row)
                
                if len(matching_messages) >= n_per_category:
                    break
            
            if not matching_messages:
                print(f"No messages found matching {category} patterns")
                continue
            
            # Test these messages
            category_df = pd.DataFrame(matching_messages)
            correct = 0
            failures = []
            
            expected_classification = self._get_expected_classification(category)
            
            for _, row in category_df.iterrows():
                message = str(row['message'])
                sender = str(row['sender_name']) if 'sender_name' in row and pd.notna(row['sender_name']) else ""
                
                prediction = self.classifier.classify_message(message, sender)
                
                is_correct = self._is_classification_correct(prediction, expected_classification)
                
                if is_correct:
                    correct += 1
                else:
                    failures.append({
                        "message": message,
                        "expected": expected_classification,
                        "predicted": prediction
                    })
            
            accuracy = (correct / len(category_df)) * 100
            results[category] = {
                "correct": correct,
                "total": len(category_df),
                "accuracy": accuracy,
                "failures": failures
            }
            
            print(f"Found {len(category_df)} messages")
            print(f"Accuracy: {correct}/{len(category_df)} ({accuracy:.1f}%)")
            
            # Show sample failures
            if failures:
                print("Sample failures:")
                for i, failure in enumerate(failures[:2], 1):
                    print(f"  {i}. Expected: {failure['expected']}")
                    print(f"     Predicted: {failure['predicted']}")
                    print(f"     Message: {failure['message'][:60]}...")
        
        return results

    def _get_expected_classification(self, category: str) -> str:
        """Map category names to expected classifications"""
        mapping = {
            "Likely OTP": "Security & Authentication - OTP verification",
            "Likely Banking": "Unknown",
            "Likely Promotional": "Unknown",
            "Likely Government": "Government & Public Services - Identity services"
        }
        return mapping.get(category, "Unknown")

    def _is_classification_correct(self, predicted: str, expected: str) -> bool:
        """Check if classification is correct, allowing for partial matches"""
        if predicted == expected:
            return True
        
        # Allow partial matches for main categories
        if "OTP verification" in expected and "OTP verification" in predicted:
            return True
        
        if "Government" in expected and "Government" in predicted:
            return True
        
        return False

    def _calculate_accuracy_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate detailed accuracy metrics"""
        
        # Overall accuracy
        correct_predictions = df['ground_truth'] == df['predicted']
        overall_accuracy = correct_predictions.sum() / len(df) * 100
        
        # Per-category accuracy
        category_results = {}
        
        for category in df['ground_truth'].unique():
            category_mask = df['ground_truth'] == category
            category_df = df[category_mask]
            
            if len(category_df) > 0:
                category_correct = (category_df['ground_truth'] == category_df['predicted']).sum()
                category_accuracy = category_correct / len(category_df) * 100
                
                category_results[category] = {
                    "correct": category_correct,
                    "total": len(category_df),
                    "accuracy": category_accuracy
                }
        
        return {
            "overall_accuracy": overall_accuracy,
            "category_results": category_results,
            "total_correct": correct_predictions.sum(),
            "total_tested": len(df)
        }

    def _print_accuracy_results(self, results: Dict, sample_df: pd.DataFrame):
        """Print detailed accuracy results"""
        
        print(f"\nResults:")
        print(f"Overall Accuracy: {results['total_correct']}/{results['total_tested']} ({results['overall_accuracy']:.1f}%)")
        
        print("\nPer-Category Breakdown:")
        for category, metrics in results["category_results"].items():
            print(f"  {category}: {metrics['correct']}/{metrics['total']} ({metrics['accuracy']:.1f}%)")
        
        # Show confusion matrix
        print("\nConfusion Matrix:")
        confusion = pd.crosstab(sample_df['ground_truth'], sample_df['predicted'], margins=True)
        print(confusion)
        
        # Show sample misclassifications
        misclassified = sample_df[sample_df['ground_truth'] != sample_df['predicted']]
        
        if len(misclassified) > 0:
            print(f"\nSample Misclassifications ({len(misclassified)} total):")
            for i, (_, row) in enumerate(misclassified.head(5).iterrows(), 1):
                print(f"\n{i}. Expected: {row['ground_truth']}")
                print(f"   Predicted: {row['predicted']}")
                print(f"   Message: {row['message'][:100]}...")

    def export_test_results(self, results: Dict, sample_df: pd.DataFrame, filename: str = None):
        """Export test results to files for detailed analysis"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"classifier_test_results_{timestamp}"
        
        # Export summary to JSON
        with open(f"{filename}_summary.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Export detailed results to CSV
        sample_df.to_csv(f"{filename}_detailed.csv", index=False)
        
        # Export misclassifications only
        misclassified = sample_df[sample_df['ground_truth'] != sample_df['predicted']]
        if len(misclassified) > 0:
            misclassified.to_csv(f"{filename}_misclassified.csv", index=False)
        
        print(f"\nTest results exported:")
        print(f"  Summary: {filename}_summary.json")
        print(f"  Detailed: {filename}_detailed.csv")
        if len(misclassified) > 0:
            print(f"  Misclassified: {filename}_misclassified.csv")

    def determine_ground_truth(self, message: str) -> str:
        """Determine the ground truth classification based on message content"""
        message_lower = message.lower()
        
        # Check for strong banking context first
        banking_score = sum(1 for pattern in self.compiled_patterns["banking_indicators"] 
                          if pattern.search(message))
        
        # Check for promotional content
        promo_score = sum(1 for pattern in self.compiled_patterns["promotional_indicators"] 
                         if pattern.search(message))
        
        # Check for OTP patterns
        otp_score = sum(1 for pattern in self.compiled_patterns["otp_indicators"] 
                       if pattern.search(message))
        
        # Check for government patterns
        gov_score = sum(1 for pattern in self.compiled_patterns["government_indicators"] 
                       if pattern.search(message))
        
        # Check for actual OTP number
        has_otp_number = bool(re.search(r'\b\d{4,8}\b', message))
        
        # Classification logic for ground truth
        # 1. If it has clear OTP patterns AND a number, it's likely an OTP
        if otp_score >= 1 and has_otp_number:
            # But check if it's a banking transaction with OTP mention
            if banking_score >= 2:  # Strong banking context
                return "Unknown"
            return "Security & Authentication - OTP verification"
        
        # 2. If it has strong banking indicators, it's banking/transaction
        if banking_score >= 2:
            return "Unknown"
        
        # 3. If it has strong promotional indicators, it's promotional
        if promo_score >= 2:
            return "Unknown"
        
        # 4. If it has government indicators but no OTP context, it's government
        if gov_score >= 1 and otp_score == 0:
            return "Government & Public Services - Identity services"
        
        # 5. If it has government + OTP, it's an OTP for government service
        if gov_score >= 1 and otp_score >= 1 and has_otp_number:
            return "Security & Authentication - OTP verification"
        
        # Default
        return "Unknown"


def main():
    """Main function to run CSV-based testing"""
    
    # Import the classifier
    try:
        from sms_classifier import SMSClassifier
        classifier = SMSClassifier()
        print("SMS Classifier imported successfully!")
    except ImportError as e:
        print(f"Error importing SMS Classifier: {e}")
        print("Make sure sms_classifier.py is in the same directory.")
        return
    
    # Initialize tester
    tester = CSVBasedTester(classifier)
    
    # Get CSV file path
    csv_file = input("\nEnter path to your CSV file: ").strip().strip('"')
    
    if not csv_file:
        print("No file path provided. Exiting.")
        return
    
    # Load CSV
    try:
        print(f"Loading CSV file: {csv_file}")
        df = pd.read_csv(csv_file, dtype=str)
        print(f"Loaded {len(df):,} messages")
        
        # Check required columns
        if 'message' not in df.columns:
            print("Error: 'message' column not found in CSV")
            return
        
        # Add sender_name if missing
        if 'sender_name' not in df.columns:
            df['sender_name'] = ""
    
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return
    
    # Show testing options
    print("\nChoose testing method:")
    print("1. Pattern-based accuracy test (automatic ground truth)")
    print("2. Manual verification test (you verify each classification)")
    print("3. Targeted category test (test specific message types)")
    print("4. Quick sample test (20 random messages with debug)")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        # Pattern-based test
        n_samples = input("Enter number of samples to test (default 200): ").strip()
        n_samples = int(n_samples) if n_samples.isdigit() else 200
        
        results, sample_df = tester.pattern_based_accuracy_test(df, n_samples)
        
        # Ask if user wants to export results
        export = input("\nExport detailed results to files? (y/n): ").lower().strip()
        if export == 'y':
            filename = input("Enter filename prefix (or press Enter for auto): ").strip()
            filename = filename if filename else None
            tester.export_test_results(results, sample_df, filename)
    
    elif choice == "2":
        # Manual verification test
        n_samples = input("Enter number of samples for manual verification (default 20): ").strip()
        n_samples = int(n_samples) if n_samples.isdigit() else 20
        
        correct, total = tester.manual_verification_test(df, n_samples)
        
        if total > 0:
            accuracy = (correct / total) * 100
            print(f"\nFinal Manual Verification Accuracy: {correct}/{total} ({accuracy:.1f}%)")
    
    elif choice == "3":
        # Targeted category test
        n_per_category = input("Enter samples per category (default 30): ").strip()
        n_per_category = int(n_per_category) if n_per_category.isdigit() else 30
        
        results = tester.targeted_category_test(df, n_per_category)
        
        # Print summary
        print("\nTargeted Test Summary:")
        print("-" * 30)
        for category, metrics in results.items():
            if metrics:
                print(f"{category}: {metrics['accuracy']:.1f}% ({metrics['correct']}/{metrics['total']})")
    
    elif choice == "4":
        # Quick sample test with debug
        print("\nQuick Sample Test with Debug:")
        print("-" * 40)
        
        sample_df = df.sample(n=min(20, len(df)), random_state=42)
        
        for i, (_, row) in enumerate(sample_df.iterrows(), 1):
            message = str(row['message'])
            sender = str(row['sender_name']) if 'sender_name' in row and pd.notna(row['sender_name']) else ""
            
            print(f"\nSample {i}:")
            print(f"Message: {message[:80]}...")
            
            classification = classifier.classify_message(message, sender)
            print(f"Classification: {classification}")
            
            # Ask if user wants debug
            debug = input("Debug this classification? (y/n): ").lower().strip()
            if debug == 'y':
                classifier.debug_classification(message, sender)
            
            if i % 5 == 0:
                continue_test = input(f"\nContinue testing? (y/n): ").lower().strip()
                if continue_test != 'y':
                    break
    
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()