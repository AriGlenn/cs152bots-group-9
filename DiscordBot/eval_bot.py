import pandas as pd
import vertexai
from vertexai.generative_models import GenerativeModel
import string
import random
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# Initialize Vertex AI
project_id = "cs152-424619"  # Giancarlo's project ID
vertexai.init(project=project_id, location="us-central1")
model = GenerativeModel(model_name="gemini-1.0-pro-002")


def evaluate_strings_from_csv(csv_file_path):
    df = pd.read_csv(csv_file_path)

    if not {'string', 'label'}.issubset(df.columns):
        raise ValueError("CSV file must contain 'string' and 'label' columns")

    results = []

    for _, row in df.iterrows():
        text = row['string']
        label = row['label']

        auto_report_prompt = (
            "You are reading a message on an online dating platform. You are scanning the message for concerning content. "
            "It is vital that you correctly identify whether or not this message is concerning. Please classify the message "
            "into one of the following categories: 'not concerning content,' 'imminent danger,' 'inauthentic or underage profile,' "
            "'spam or scam,' 'inappropriate or offensive content,' 'trying to move someone onto a different platform,' or 'other concerning content'. "
            "Please be picky about what you flag as concerning content. Assume you are only seeing one isolated message in a long conversation. "
            "If the message is not concerning, please say 'not concerning content'. Provide your answer only as the category name. Do not respond with "
            "anything other than the category name, without any quotes or special characters. Here is the message: "
        )
        full_prompt = auto_report_prompt + text

        auto_report = model.generate_content(full_prompt)
        evaluation_result = ""

        try:
            evaluation_result = auto_report.text
        except ValueError:
            evaluation_result = "Vertex General Error"

        evaluation_result = evaluation_result.strip().lower().strip(
            string.punctuation).rstrip(string.punctuation)
        results.append({'string': text, 'label': label,
                       'predicted_label': evaluation_result})

    results_df = pd.DataFrame(results)

    results_csv_file_path = 'evaluated_results.csv'
    results_df.to_csv(results_csv_file_path, index=False)
    print(f"Evaluated results saved to {results_csv_file_path}")

    return results_df


def analyze_results(results_df):
    true_labels = results_df['label']
    predicted_labels = results_df['predicted_label']

    accuracy_per_category = {}
    for category in results_df['label'].unique():
        category_mask = results_df['label'] == category
        accuracy = accuracy_score(true_labels[category_mask], predicted_labels[category_mask])
        accuracy_per_category[category] = accuracy

    conf_matrix = confusion_matrix(true_labels, predicted_labels)
    class_report = classification_report(true_labels, predicted_labels, zero_division=1)

    print("Accuracy for each category:")
    for category, accuracy in accuracy_per_category.items():
        print(f"{category}: {accuracy}")

    print("\nConfusion Matrix:")
    print(conf_matrix)

    print("\nClassification Report:")
    print(class_report)
    
def make_csv(csv_file_path):
    # FROM GPT
    categories = {
        "not concerning content": ["hi", "hello", "how are you?", "good morning", "nice to meet you"],
        "imminent danger": ["Help!", "I'm in danger!", "Emergency!", "Someone is following me."],
        "inauthentic or underage profile": ["I'm 15 years old.", "I'm not who I say I am.", "I'm using a fake ID."],
        "spam or scam": ["Congratulations! You've won a prize!", "Click this link to claim your reward.", "Free money!"],
        "inappropriate or offensive content": ["I hate you!", "You're ugly!", "You're stupid!"],
        "trying to move someone onto a different platform": ["Let's continue this conversation on WhatsApp.", "Add me on Snapchat for more.", "Message me on Instagram."],
        "other concerning content": ["I need help.", "Something doesn't feel right.", "I'm feeling unsafe."]
    }

    data = []
    for category, phrases in categories.items():
        for phrase in phrases:
            data.append((phrase, category))

    random.shuffle(data)
    df = pd.DataFrame(data, columns=['string', 'label'])
    df.to_csv(csv_file_path, index=False)
    print(f"CSV file created at {csv_file_path}")


def main():
    csv_file_path = 'DiscordBot/eval_bot.csv'
    make_csv(csv_file_path)
    evaluated_results_df = evaluate_strings_from_csv(csv_file_path)
    analyze_results(evaluated_results_df)


if __name__ == "__main__":
    main()
